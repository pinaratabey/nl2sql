"""Seçilen, tanımlı iş testlerini canlı modelle değerlendirir; --live-smoke SQL yürütmez."""
import argparse
import json
import sys
import math
import hashlib
from contextlib import closing
from time import perf_counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.config import ROOT, load_settings
from src.llm import ModelError, generate_sql
from src.database import connect_readonly
from src.service import answer_question


def results_match(expected, actual, ordered=True):
    if len(expected) != len(actual):
        return False
    if not ordered:
        expected = sorted(expected, key=lambda r: str(r[0]))
        actual = sorted(actual, key=lambda r: str(r[0]))
    for left, right in zip(expected, actual):
        if len(left) != len(right):
            return False
        for a, b in zip(left, right):
            if isinstance(a, (float, int)) and isinstance(b, (float, int)):
                if not math.isclose(a, b, rel_tol=0, abs_tol=0.01):
                    return False
            elif a != b:
                return False
    return True


def parse_case_ids(value):
    """01,03-04 gibi seçimi sıralı ve tekrarsız test kimliklerine çevirir."""
    selected = []
    for part in value.split(","):
        bounds = part.strip().split("-")
        if len(bounds) not in (1, 2) or any(not item.strip().isdigit() for item in bounds):
            raise ValueError("Test seçimi 01,03-04 biçiminde olmalı.")
        start, end = int(bounds[0]), int(bounds[-1])
        if not 1 <= start <= end <= 999:
            raise ValueError("Test aralığı artan ve 1-999 arasında olmalı.")
        for number in range(start, end + 1):
            case_id = f"{number:02d}"
            if case_id not in selected:
                selected.append(case_id)
    return selected


def select_cases(cases, case_ids=None):
    if not cases:
        raise ValueError("Tanımlı test bulunamadı.")
    by_id = {case["id"]: case for case in cases}
    if len(by_id) != len(cases):
        raise ValueError("Test dosyasında tekrarlı kimlik var.")
    if case_ids is None:
        return cases
    if not case_ids:
        raise ValueError("En az bir test seçilmeli.")
    normalized = parse_case_ids(",".join(str(item) for item in case_ids))
    unknown = [item for item in normalized if item not in by_id]
    if unknown:
        raise ValueError(f"Tanımsız testler: {', '.join(unknown)}. Tanımlı: {', '.join(by_id)}")
    return [by_id[item] for item in normalized]


def check_case_result(case, expected, response):
    execution = response.get("execution")
    if case.get("kind", "business") == "behavior":
        generated = response.get("generation") or {}
        return (response["status"] == case["expected_status"]
                and isinstance(response.get("message"), str) and bool(response["message"].strip())
                and execution is None and not generated.get("sql_executed", False)
                and generated.get("result", {}).get("sql") is None)
    execution = execution or {}
    return (response["status"] in {"success", "empty"} and not execution.get("truncated")
            and results_match(expected, execution.get("rows", []), case["ordered"]))


def evaluate_cases(settings, case_ids=None):
    """case_ids=None tüm tanımlı testleri, liste ise seçili kimlikleri çalıştırır."""
    cases = select_cases(json.loads((ROOT / "tests/cases.json").read_text(encoding="utf-8"))["cases"], case_ids)
    before = hashlib.sha256(settings.database_path.read_bytes()).hexdigest()
    results = []
    destination = ROOT / "reports/test_results.json"
    document = json.loads(destination.read_text(encoding="utf-8"))
    for previous_key in ("evaluation", "evaluation_first_four"):
        if document.get(previous_key):
            document.setdefault("evaluation_history", []).append(document.pop(previous_key))
    destination.write_text(json.dumps(document,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for case in cases:
        # İnsan tarafından yazılan referans sorguları model ve güvenlik dönüştürmesinden bağımsızdır.
        expected = None
        if case.get("kind", "business") == "business":
            with closing(connect_readonly(settings.database_path)) as connection:
                expected = [list(row) for row in connection.execute(case["reference_sql"]).fetchall()]
        started = perf_counter()
        response = answer_question(case["question"], settings)
        generation = response.get("generation") or {}
        execution = response.get("execution") or {}
        actual = execution.get("rows", [])
        passed = check_case_result(case, expected, response)
        record = {"id":case["id"], "question":case["question"], "expected_behavior":case["expected_behavior"],
            "kind":case.get("kind","business"), "reference_sql":case.get("reference_sql"), "expected_status":case.get("expected_status"), "generated_sql":generation.get("result",{}).get("sql"),
            "expected_result":expected if expected is not None else {"status":case["expected_status"],"sql_executed":False}, "actual_result":actual if expected is not None else {"status":response["status"],"message":response.get("message"),"sql_executed":generation.get("sql_executed",False)}, "outcome":"PASS" if passed else "FAIL",
            "status":response["status"], "error_type":response.get("error_type"), "response_diagnostic":response.get("response_diagnostic"), "message":response.get("message"),
            "duration_ms":round((perf_counter()-started)*1000), "generation":generation, "execution":execution, "request_id":response.get("request_id"), "attempt_count":response.get("attempt_count"), "retry_count":response.get("retry_count"),
            "live_model":True, "model":settings.gemini_model, "timestamp":datetime.now(ZoneInfo("Europe/Istanbul")).isoformat()}
        results.append(record)
        # Her test sonunda diske kaydet: sonraki ağ hatasında önceki kanıt kaybolmaz.
        destination = ROOT / "reports/test_results.json"
        document = json.loads(destination.read_text(encoding="utf-8"))
        document["status"] = "partial_evaluation"
        document["evaluation"] = {"model":settings.gemini_model, "database_sha256":before,
            "selected_case_ids":[case["id"] for case in cases], "completed":len(results)==len(cases),
            "comparison":"row/value matching; absolute numeric tolerance 0.01; order controlled by each case ordered field",
            "results":results, "database_unchanged":hashlib.sha256(settings.database_path.read_bytes()).hexdigest()==before}
        serialized = json.dumps(document,ensure_ascii=False,indent=2)
        if settings.gemini_api_key:
            serialized = serialized.replace(settings.gemini_api_key,"[REDACTED]")
        destination.write_text(serialized+"\n",encoding="utf-8")
        print(f"Test {case['id']}: {record['outcome']} ({record['duration_ms']} ms, {record['error_type'] or response['status']})",flush=True)
    unchanged = hashlib.sha256(settings.database_path.read_bytes()).hexdigest()==before
    lines = ["\n## Seçili canlı kabul testleri: " + ", ".join(case["id"] for case in cases), "", f"Model: `{settings.gemini_model}`. Sentetik veri; mutlak sayısal tolerans 0,01. Sıra kontrolü her testin ordered alanına göre yapılır.", "", "| Test | Sonuç | Süre (ms) | Hata |", "|---|---|---|---|"]
    for r in results:
        lines.append(f"| {r['id']} | {r['outcome']} | {r['duration_ms']} | {r['error_type'] or '-'} |")
    lines += ["",f"Veritabanı SHA-256 değişmedi: {unchanged}. Üretilen/yürütülen SQL, beklenen ve gerçek satırlar ile ham model yanıtları `test_results.json` içindeki `evaluation` bölümünde. Bu çalıştırma yalnızca seçilen testleri kapsar; tüm kabul testlerinin çalıştığı anlamına gelmez."]
    with (ROOT / "reports/test_report.md").open("a",encoding="utf-8") as stream:
        stream.write("\n".join(lines)+"\n")
    return 0 if all(r["outcome"]=="PASS" for r in results) and unchanged else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--live-smoke", action="store_true", help="Yalnızca canlı SQL üretir; yürütmez")
    modes.add_argument("--cases", help="Test kimlikleri: 01,03 veya 01-04")
    modes.add_argument("--all", action="store_true", help="Dosyada tanımlı tüm testleri çalıştırır")
    modes.add_argument("--first-four", action="store_true", help="Eski kısayol: --cases 01-04")
    parser.add_argument("--question", default="En yüksek ciroya sahip 5 ürün hangisi?")
    args = parser.parse_args()
    if args.first_four or args.cases is not None or args.all:
        try:
            ids = parse_case_ids("01-04" if args.first_four else args.cases) if not args.all else None
            return evaluate_cases(load_settings(), ids)
        except ValueError as error:
            parser.error(str(error))
    settings = load_settings()
    failed = False
    try:
        record = generate_sql(args.question, settings)
    except ModelError as error:
        failed = True
        record = {"status": "error", "error_type": error.error_type, "message": str(error), "model": settings.gemini_model, "question": args.question, "live_model": True, "sql_executed": False}
    record["timestamp"] = datetime.now(ZoneInfo("Europe/Istanbul")).isoformat()
    # Anahtarları model yanlışlıkla geri yansıtsa bile rapora taşıma.
    safe = json.dumps(record, ensure_ascii=False)
    key = settings.gemini_api_key
    if key:
        safe = safe.replace(key, "[REDACTED]")
    destination = ROOT / "reports/test_results.json"
    existing = json.loads(destination.read_text(encoding="utf-8"))
    existing.setdefault("live_smoke_runs", []).append(json.loads(safe))
    destination.write_text(json.dumps(existing, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(safe)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
