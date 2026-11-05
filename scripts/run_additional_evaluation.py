"""Ek kabul testlerini canlı Gemini üzerinden çalıştır ve ayrı bir rapor yaz."""
import hashlib
import json
from contextlib import closing
from datetime import datetime
from zoneinfo import ZoneInfo

from run_evaluation import ROOT, answer_question, check_case_result, connect_readonly, load_settings


def main():
    settings = load_settings()
    cases = json.loads((ROOT / "tests/additional_cases.json").read_text(encoding="utf-8"))
    destination = ROOT / "reports/additional_test_results.json"
    database_hash = hashlib.sha256(settings.database_path.read_bytes()).hexdigest()
    report = {
        "model": settings.gemini_model,
        "started_at": datetime.now(ZoneInfo("Europe/Istanbul")).isoformat(),
        "database_sha256": database_hash,
        "database_unchanged": True,
        "completed": False,
        "results": [],
    }
    # Referans sorgularının tümünü ilk API isteğinden önce doğrula.
    with closing(connect_readonly(settings.database_path)) as connection:
        expected_results = {
            case["id"]: [list(row) for row in connection.execute(case["reference_sql"])]
            for case in cases if "reference_sql" in case
        }
    for case in cases:
        expected = expected_results.get(case["id"])
        behavior = "expected_status" in case
        criteria = {**case, "kind": "behavior" if behavior else "business", "ordered": True}
        response = answer_question(case["question"], settings)
        generation = response["generation"] or {}
        execution = response["execution"]
        expected_status = case["expected_status"] if behavior else ("success" if expected else "empty")
        passed = response["status"] == expected_status and check_case_result(criteria, expected, response)
        record = {
            **case,
            "expected_status": expected_status,
            "expected_rows": expected,
            "actual_rows": execution["rows"] if execution is not None else None,
            "status": response["status"],
            "error_type": response["error_type"],
            "message": response["message"],
            "generated_sql": generation.get("result", {}).get("sql"),
            "executed_sql": execution.get("executed_sql") if execution is not None else None,
            "sql_executed": generation.get("sql_executed", False),
            "truncated": execution.get("truncated") if execution is not None else None,
            "duration_ms": response["duration_ms"],
            "automated_outcome": "PASS" if passed else "FAIL",
        }
        report["results"].append(record)
        report["database_unchanged"] = hashlib.sha256(settings.database_path.read_bytes()).hexdigest() == database_hash
        report["completed"] = len(report["results"]) == len(cases)
        serialized = json.dumps(report, ensure_ascii=False, indent=2)
        if settings.gemini_api_key:
            serialized = serialized.replace(settings.gemini_api_key, "[REDACTED]")
        destination.write_text(serialized + "\n", encoding="utf-8")
        print(f"{case['id']}: {record['automated_outcome']} ({response['error_type'] or response['status']})", flush=True)
    return 0 if report["database_unchanged"] and all(
        record["automated_outcome"] == "PASS" for record in report["results"]
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
