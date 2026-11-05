"""Ortam, sabit iş kuralı ve salt-okunur bağlantı kontrolleri; canlı LLM testi değildir."""
import sqlite3
import pytest
from src.config import load_settings
from src.database import connect_readonly


def test_fixed_reference_date(monkeypatch):
    monkeypatch.setenv("REFERENCE_DATE", "2026-06-30")
    assert load_settings().reference_date.isoformat() == "2026-06-30"
    monkeypatch.setenv("REFERENCE_DATE", "2026-11-02")
    with pytest.raises(ValueError):
        load_settings()


def test_missing_database_is_not_created(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(FileNotFoundError):
        connect_readonly(path)
    assert not path.exists()


def test_readonly_connection_rejects_write(tmp_path):
    path = tmp_path / "fixture.db"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE sample (id INTEGER)")
    connection = connect_readonly(path)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute("INSERT INTO sample VALUES (1)")
        assert connection.execute("SELECT COUNT(*) FROM sample").fetchone()[0] == 0
    finally:
        connection.close()


def test_synthetic_dataset_integrity_and_reproducibility(tmp_path):
    from scripts.setup_db import create_dataset
    from src.schema import inspect_schema, schema_context
    first, second = tmp_path / "first.db", tmp_path / "second.db"
    summary = create_dataset(first)
    assert create_dataset(second) == summary
    with sqlite3.connect(first) as a, sqlite3.connect(second) as b:
        assert list(a.iterdump()) == list(b.iterdump())
        assert a.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert a.execute("PRAGMA foreign_key_check").fetchall() == []
        assert a.execute("SELECT MIN(OrderDate), MAX(OrderDate) FROM Orders").fetchone() == ("2025-07-01", "2026-06-30")
        assert a.execute("SELECT COUNT(*) FROM Customers c WHERE NOT EXISTS (SELECT 1 FROM Orders o WHERE o.CustomerID=c.CustomerID)").fetchone()[0] == 30
        assert a.execute("SELECT COUNT(DISTINCT substr(OrderDate,1,7)) FROM Orders").fetchone()[0] == 12
        assert a.execute("SELECT COUNT(DISTINCT Category) FROM Products").fetchone()[0] == 6
        assert a.execute("SELECT COUNT(DISTINCT Segment) FROM Customers").fetchone()[0] == 3
        assert a.execute("SELECT COUNT(DISTINCT Name) FROM Customers").fetchone()[0] == 300
        assert a.execute("SELECT COUNT(*) FROM Customers WHERE Name LIKE 'Sentetik%'").fetchone()[0] == 0
        assert a.execute("SELECT COUNT(*) FROM Products WHERE ProductName LIKE 'Sentetik%'").fetchone()[0] == 0
        assert {r[0] for r in a.execute("SELECT DISTINCT Category FROM Products")} == {"Temel Gıda", "Süt ve Kahvaltılık", "İçecek", "Atıştırmalık", "Ev Temizliği", "Kişisel Bakım"}
        assert a.execute("SELECT COUNT(*) FROM OrderItems i JOIN Products p ON p.ProductID=i.ProductID WHERE i.UnitPrice != p.Price").fetchone()[0] > 0
    schema = inspect_schema(first)
    assert schema["Orders"]["row_count"] == 2400
    assert sum(len(t["foreign_keys"]) for t in schema.values()) == 3
    assert "CustomerID INTEGER PK" in schema_context(first)
    with pytest.raises(FileExistsError):
        create_dataset(first)


def test_gemini_errors_are_controlled_and_do_not_expose_key(monkeypatch):
    from dataclasses import replace
    import requests
    from src.llm import generate_sql, ModelError
    settings = replace(load_settings(), gemini_api_key="test-secret", gemini_model="test-model")
    monkeypatch.setattr("src.llm.build_system_prompt", lambda _: "test schema")
    def timeout(*args, **kwargs):
        raise requests.Timeout("test-secret")
    monkeypatch.setattr("src.llm.requests.post", timeout)
    with pytest.raises(ModelError) as caught:
        generate_sql("Ciro?", settings)
    assert caught.value.error_type == "model_timeout"
    assert "test-secret" not in str(caught.value)
    assert "test-secret" not in repr(settings)


def test_gemini_rejects_incomplete_response(monkeypatch):
    from dataclasses import replace
    from types import SimpleNamespace
    from src.llm import generate_sql, ModelError
    settings = replace(load_settings(), gemini_api_key="test-secret", gemini_model="test-model")
    monkeypatch.setattr("src.llm.build_system_prompt", lambda _: "test schema")
    response = SimpleNamespace(status_code=200, json=lambda: {"candidates": [{"finishReason": "MAX_TOKENS"}]})
    monkeypatch.setattr("src.llm.requests.post", lambda *a, **k: response)
    with pytest.raises(ModelError) as caught:
        generate_sql("Ciro?", settings)
    assert caught.value.error_type == "invalid_model_response"


@pytest.fixture(scope="module")
def analytics_path(tmp_path_factory):
    from scripts.setup_db import create_dataset
    path = tmp_path_factory.mktemp("analytics") / "analytics.db"
    create_dataset(path)
    return path


@pytest.mark.parametrize("sql", [
    "DELETE FROM Customers", "SELECT * FROM Customers; DELETE FROM Customers",
    "SELECT * FROM sqlite_master", "SELECT * FROM sqlite_schema",
    "WITH x AS (SELECT * FROM sqlite_master) SELECT * FROM x",
    "SELECT * FROM Customers WHERE EXISTS (SELECT 1 FROM sqlite_master)",
    "SELECT load_extension('x')", "SELECT readfile('x')", "SELECT * FROM pragma_table_info('Customers')",
    "ATTACH DATABASE 'x.db' AS x; PRAGMA table_info(Customers)",
    "SELECT * FROM main.Customers", "SELECT BirthDate FROM Customers",
    "WITH x AS (DELETE FROM Customers RETURNING *) SELECT * FROM x",
    "SELECT * FROM Customers UNION SELECT * FROM secret",
    "SELECT c.Name FROM Customers c JOIN Orders o ON c.Missing=o.OrderID",
])
def test_sql_security_rejects_unsafe_input(analytics_path, sql):
    from src.database import execute_query
    from src.sql_security import SQLSecurityError
    with pytest.raises(SQLSecurityError):
        execute_query(sql, analytics_path)


def test_comments_ctes_and_literals_are_safe(analytics_path):
    from src.database import execute_query
    before = execute_query("SELECT COUNT(*) FROM Customers", analytics_path)["rows"]
    result = execute_query("WITH x AS (SELECT CustomerID FROM Customers) SELECT * FROM x /* DELETE FROM Customers */ LIMIT 2", analytics_path)
    assert result["row_count"] == 2
    assert "DELETE" not in result["executed_sql"]
    assert execute_query("SELECT '-- /* literal */'", analytics_path)["rows"] == [["-- /* literal */"]]
    assert execute_query("SELECT COUNT(*) FROM Customers", analytics_path)["rows"] == before


def test_row_limit_and_timeout(analytics_path):
    from src.database import execute_query, QueryError
    result = execute_query("SELECT OrderID FROM Orders ORDER BY OrderID", analytics_path)
    assert result["row_count"] == 500 and result["truncated"]
    assert execute_query("SELECT OrderID FROM Orders LIMIT 3", analytics_path)["row_count"] == 3
    with pytest.raises(QueryError) as caught:
        execute_query("SELECT SUM(a.Quantity*b.Quantity*c.Quantity) FROM OrderItems a CROSS JOIN OrderItems b CROSS JOIN OrderItems c", analytics_path, timeout_seconds=0.001)
    assert caught.value.error_type == "query_timeout"


def test_reference_queries_execute(analytics_path):
    import json
    from pathlib import Path
    from src.database import execute_query
    cases = json.loads((Path(__file__).parents[1]/"tests/cases.json").read_text(encoding="utf-8"))["cases"]
    for case, expected_rows in zip(cases, [5, 1, 6, 6]):
        result = execute_query(case["reference_sql"], analytics_path)
        assert result["row_count"] == expected_rows


@pytest.mark.parametrize("sql", ["DELETE FROM Customers", "SELECT * FROM sqlite_master", "SELECT load_extension('x')"])
def test_database_defense_without_ast(analytics_path, monkeypatch, sql):
    from src.database import execute_query, QueryError
    # AST bozulsa bile DB authorizer/salt-okunur bağlantı engellemeli.
    monkeypatch.setattr("src.sql_security.validate_sql", lambda sql, schema: sql)
    with pytest.raises(QueryError):
        execute_query(sql, analytics_path)


def test_result_comparison_checks_order_and_values():
    from scripts.run_evaluation import results_match
    assert results_match([["a", 1.00]], [["a", 1.001]])
    assert not results_match([["a", 1]], [["a", 2]])
    assert not results_match([["a", 1],["b",2]], [["b",2],["a",1]])
    assert results_match([["a", 1],["b",2]], [["b",2],["a",1]], ordered=False)


@pytest.mark.parametrize("status,sql,valid", [("ok","SELECT 1",True),("clarification",None,False),("rejected",None,False)])
def test_model_optional_success_message(monkeypatch, status, sql, valid):
    import json
    from dataclasses import replace
    from types import SimpleNamespace
    from src.llm import generate_sql, ModelError
    settings = replace(load_settings(), gemini_api_key="test-secret", gemini_model="test-model")
    monkeypatch.setattr("src.llm.build_system_prompt", lambda _: "test schema")
    response = SimpleNamespace(status_code=200, json=lambda: {"candidates":[{"finishReason":"STOP","content":{"parts":[{"text":json.dumps({"status":status,"sql":sql,"message":None})}]}}]})
    monkeypatch.setattr("src.llm.requests.post", lambda *a, **k: response)
    if valid:
        record = generate_sql("test",settings)
        assert record["result"]["sql"] == sql
        assert record["result"]["message"] == ""
    else:
        with pytest.raises(ModelError):
            generate_sql("test",settings)


def test_case_selection_and_ranges():
    from scripts.run_evaluation import parse_case_ids, select_cases
    cases = [{"id":f"{n:02d}"} for n in range(1,5)]
    assert parse_case_ids("3,01-02,3") == ["03","01","02"]
    assert [c["id"] for c in select_cases(cases,[3,1])] == ["03","01"]
    assert select_cases(cases) == cases
    for invalid in ["", "4-2", "0", "a", "1,", "1-1000"]:
        with pytest.raises(ValueError):
            parse_case_ids(invalid)
    with pytest.raises(ValueError, match="Tanımsız"):
        select_cases(cases,["05"])
    with pytest.raises(ValueError):
        select_cases(cases,[])


def test_selected_evaluation_runs_only_requested_cases(tmp_path, analytics_path, monkeypatch):
    import json
    from dataclasses import replace
    from scripts import run_evaluation as runner
    (tmp_path/"tests").mkdir()
    (tmp_path/"reports").mkdir()
    cases = [{"id":f"{n:02d}","question":f"soru-{n}","expected_behavior":"tek değer","ordered":True,"reference_sql":f"SELECT {n}"} for n in range(1,5)]
    (tmp_path/"tests/cases.json").write_text(json.dumps({"cases":cases}),encoding="utf-8")
    previous = {"results":[{"id":"01","outcome":"PASS"}]}
    (tmp_path/"reports/test_results.json").write_text(json.dumps({"evaluation_first_four":previous}),encoding="utf-8")
    monkeypatch.setattr(runner,"ROOT",tmp_path)
    called = []
    def answer(question, settings):
        called.append(question)
        number = int(question.split("-")[-1])
        return {"status":"success","generation":{"result":{"sql":f"SELECT {number}"}},"execution":{"rows":[[number]],"truncated":False}}
    monkeypatch.setattr(runner,"answer_question",answer)
    settings = replace(load_settings(),database_path=analytics_path,gemini_api_key="test-secret")
    assert runner.evaluate_cases(settings,["04","02"]) == 0
    assert called == ["soru-4","soru-2"]
    saved = json.loads((tmp_path/"reports/test_results.json").read_text(encoding="utf-8"))
    assert saved["evaluation"]["selected_case_ids"] == ["04","02"]
    assert saved["evaluation"]["completed"]
    assert saved["evaluation_history"] == [previous]
    assert saved["evaluation"]["database_unchanged"]
    with pytest.raises(ValueError):
        runner.evaluate_cases(settings,["99"])
    assert called == ["soru-4","soru-2"]


@pytest.mark.parametrize("status", ["success", "empty", "clarification", "rejected", "error"])
def test_ui_uses_service_and_displays_status(monkeypatch, analytics_path, status):
    from dataclasses import replace
    from pathlib import Path
    import pandas  # Windows soğuk native importunu AppTest iş parçacığından önce tamamla.
    from streamlit.testing.v1 import AppTest
    settings = replace(load_settings(), database_path=analytics_path,gemini_api_key="ui-test-secret",gemini_model="test-model")
    monkeypatch.setattr("src.config.load_settings",lambda: settings)
    called = []
    def answer(question, settings):
        called.append(question)
        execution = {"rows":[[1]],"columns":["count"],"row_count":1,"truncated":True,"duration_ms":2} if status=="success" else None
        return {"status":status,"message":"Kontrollü yanıt", "error_type":"test_error" if status=="error" else None,
                "generation":{"result":{"sql":"SELECT COUNT(*) FROM Customers"}} if status in {"success","empty","error"} else None,
                "execution":execution}
    monkeypatch.setattr("src.service.answer_question",answer)
    app = AppTest.from_file(str(Path(__file__).parents[1]/"app.py"), default_timeout=15).run()
    assert not app.exception
    app.text_area[0].set_value("Müşteri sayısı?")
    next(button for button in app.button if button.label == "Sorgula").click().run()
    assert not app.exception
    assert called == ["Müşteri sayısı?"]
    assert "ui-test-secret" not in str(app)
    if status=="success":
        assert len(app.dataframe)==1
        assert any("ilk 500" in w.value for w in app.warning)
    elif status=="error":
        assert app.error[0].value == "Kontrollü yanıt"
    elif status=="rejected":
        assert app.warning[0].value == "Kontrollü yanıt"
    else:
        assert len(app.info)==1
    # Rerun tekrar model çağrısı yapmaz; boş gönderim eski sonucu temizler.
    app.run()
    assert called == ["Müşteri sayısı?"]
    app.text_area[0].set_value("   ")
    next(button for button in app.button if button.label == "Sorgula").click().run()
    assert called == ["Müşteri sayısı?"]
    assert len(app.dataframe)==0 and len(app.code)==0


@pytest.mark.parametrize("scenario,expected,retries", [
    ("success","success",0),("empty","empty",0),("clarification","clarification",0),
    ("rejected","rejected",0),("unknown_field","error",0),("invalid_sql","error",0),
    ("timeout_once","success",1),("timeout_twice","error",1),("quota","error",0),
    ("missing_db","error",0),
])
def test_service_errors_retry_and_json_log(monkeypatch, analytics_path, tmp_path, scenario, expected, retries):
    import json
    from dataclasses import replace
    from src.service import answer_question
    from src.llm import ModelError
    settings = replace(load_settings(),database_path=analytics_path,gemini_api_key="log-test-secret",log_path=tmp_path/"events.jsonl")
    calls = []
    def generate(question, settings):
        calls.append(question)
        if scenario=="timeout_twice" or (scenario=="timeout_once" and len(calls)==1):
            raise ModelError("model_timeout","timeout")
        if scenario=="quota":
            raise ModelError("rate_limit","quota")
        status = scenario if scenario in {"clarification","rejected"} else "ok"
        sql = {"empty":"SELECT Name FROM Customers WHERE 1=0","unknown_field":"SELECT BirthDate FROM Customers","invalid_sql":"DELETE FROM Customers"}.get(scenario,"SELECT COUNT(*) FROM Customers") if status=="ok" else None
        return {"result":{"status":status,"sql":sql,"message":"Lütfen metriği belirtin."},"sql_executed":False}
    monkeypatch.setattr("src.service.generate_sql",generate)
    if scenario=="missing_db":
        settings = replace(settings,database_path=tmp_path/"missing.db")
    response = answer_question("soru log-test-secret",settings)
    assert response["status"]==expected
    assert response["retry_count"]==retries
    assert len(calls)==1+retries
    if expected in {"error","clarification","rejected"}:
        assert response["execution"] is None
    raw = settings.log_path.read_text(encoding="utf-8")
    assert "log-test-secret" not in raw
    events = [json.loads(line) for line in raw.splitlines()]
    assert len(events)==1
    event=events[0]
    assert event["request_id"] == response["request_id"]
    assert event["status"]==expected
    assert event["attempt_count"]==len(calls)
    assert len(event["attempts"])==len(calls)
    assert event["duration_ms"]>=0
    assert event["error_type"] == response["error_type"]
    if scenario=="timeout_twice":
        assert response["error_type"]=="model_timeout"
    if scenario in {"invalid_sql","unknown_field"}:
        assert event["executed_sql"] is None


def test_log_failure_does_not_repeat_execution(monkeypatch, analytics_path, tmp_path):
    from dataclasses import replace
    from src.service import answer_question
    settings=replace(load_settings(),database_path=analytics_path,log_path=tmp_path)
    calls=[]
    def generate(*args):
        calls.append(1)
        return {"result":{"status":"ok","sql":"SELECT COUNT(*) FROM Customers","message":""}}
    monkeypatch.setattr("src.service.generate_sql",generate)
    response=answer_question("Müşteri sayısı?",settings)
    assert response["status"]=="success" and response.get("log_warning")
    assert calls==[1]


def test_preset_question_fills_input_without_model_call(monkeypatch, analytics_path):
    from dataclasses import replace
    from pathlib import Path
    import pandas
    from streamlit.testing.v1 import AppTest
    settings=replace(load_settings(),database_path=analytics_path,gemini_api_key="ui-test-secret")
    monkeypatch.setattr("src.config.load_settings",lambda: settings)
    def unexpected_call(*args):
        raise AssertionError("Hazır soru seçimi API çağırmamalı")
    monkeypatch.setattr("src.service.answer_question",unexpected_call)
    app=AppTest.from_file(str(Path(__file__).parents[1]/"app.py"),default_timeout=15).run()
    assert not app.exception
    assert len(app.sidebar)==0
    app.button(key="preset_0").click().run()
    assert not app.exception
    assert app.text_area[0].value=="En yüksek ciroya sahip 5 ürün hangisi?"
    app.text_area[0].set_value("Elle düzenlendi")
    app.button(key="preset_2").click().run()
    assert app.text_area[0].value=="Son 6 ayın aylık ciro trendi nedir?"
    assert "last_answer" not in app.session_state


@pytest.mark.parametrize("status,sql,executed,expected", [
    ("clarification",None,False,True),("success","SELECT 1",True,False),
    ("clarification","SELECT 1",False,False),("error",None,False,False),
])
def test_behavior_checks_do_not_accept_silent_sql(status, sql, executed, expected):
    from scripts.run_evaluation import check_case_result
    case={"kind":"behavior","expected_status":"clarification"}
    response={"status":status,"message":"Hangi metriği kullanmalıyım?","generation":{"result":{"sql":sql},"sql_executed":executed},"execution":None}
    assert bool(check_case_result(case,None,response)) is expected


def test_model_offline_retries_once_without_execution(monkeypatch, analytics_path, tmp_path):
    import requests,json
    from dataclasses import replace
    from src.service import answer_question
    settings=replace(load_settings(),database_path=analytics_path,gemini_api_key="offline-test-key",log_path=tmp_path/"offline.jsonl")
    calls=[]
    def offline(*args,**kwargs):
        calls.append(1)
        raise requests.ConnectionError("offline")
    def forbidden_execution(*args,**kwargs):
        raise AssertionError("Kapalı modelde SQL yürütülmemeli")
    monkeypatch.setattr("src.llm.requests.post",offline)
    monkeypatch.setattr("src.service.execute_query",forbidden_execution)
    result=answer_question("İzmir'in toplam cirosu nedir?",settings)
    assert result["status"]=="error" and result["error_type"]=="model_unavailable"
    assert result["execution"] is None and result["generation"] is None
    assert len(calls)==2 and result["retry_count"]==1
    event=json.loads(settings.log_path.read_text(encoding="utf-8"))
    assert event["executed_sql"] is None and event["attempt_count"]==2


def test_reference_dates_ignore_system_today(monkeypatch, analytics_path):
    from datetime import date
    from dataclasses import replace
    from src.llm import build_system_prompt
    class NoSystemDate(date):
        @classmethod
        def today(cls):
            raise AssertionError("Sistem tarihi kullanılmamalı")
    monkeypatch.setattr("src.config.date",NoSystemDate)
    settings=replace(load_settings(),database_path=analytics_path)
    prompt=build_system_prompt(settings)
    assert "2026-06-30" in prompt
    for interval in ["2026-01-01..2026-06-30","2026-01-01..2026-03-31","2026-06-01..2026-06-30","2026-04-02..2026-06-30"]:
        assert interval in prompt


def test_quarter_and_last_30_days_boundaries(tmp_path):
    import json,sqlite3
    from pathlib import Path
    from scripts.setup_db import create_dataset
    from src.database import execute_query
    path=tmp_path/"boundaries.db"
    create_dataset(path)
    with sqlite3.connect(path) as c:
        c.execute("DELETE FROM OrderItems")
        c.execute("DELETE FROM Orders")
        c.execute("UPDATE Customers SET City='İzmir' WHERE CustomerID=1")
        c.execute("UPDATE Customers SET City='Ankara' WHERE CustomerID=2")
        fixtures=[("2025-12-31",2,1,1000),("2026-01-01",1,1,10),("2026-03-31",1,1,20),("2026-04-01",2,1,2000),("2026-05-31",2,1,3000),("2026-06-01",2,2,40),("2026-06-30",2,2,50)]
        for i,(day,customer,product,value) in enumerate(fixtures,1):
            c.execute("INSERT INTO Orders VALUES (?,?,?)",(i,customer,day))
            c.execute("INSERT INTO OrderItems VALUES (?,?,?,?,?)",(i,i,product,1,value))
    cases={c["id"]:c for c in json.loads((Path(__file__).parents[1]/"tests/cases.json").read_text(encoding="utf-8"))["cases"]}
    assert execute_query(cases["07"]["reference_sql"],path)["rows"]==[["İzmir",30.0]]
    assert execute_query(cases["08"]["reference_sql"],path)["rows"]==[["Tam Yağlı Süt 1 L",90.0]]


@pytest.mark.parametrize("review_result", ["corrected", "unsafe", "unavailable"])
def test_second_sql_review_gates_execution(monkeypatch, analytics_path, tmp_path, review_result):
    import json
    from dataclasses import replace
    from src.llm import ModelError
    from src.service import answer_question

    settings = replace(load_settings(), database_path=analytics_path,
                       log_path=tmp_path / "events.jsonl", review_sql=True)
    initial = "SELECT COUNT(*) FROM Products"
    calls = []

    def generate(question, settings, *, candidate_sql=None):
        calls.append((json.loads(question), candidate_sql))
        if candidate_sql is None:
            sql = initial
        elif review_result == "unavailable":
            raise ModelError("model_timeout", "timeout")
        elif review_result == "unsafe":
            sql = "DELETE FROM Customers"
        else:
            sql = "SELECT COUNT(*) FROM Customers"
        return {"result": {"status": "ok", "sql": sql}, "sql_executed": False}

    monkeypatch.setattr("src.service.generate_sql", generate)
    context = [{"question": "Kaç ürün var?"}]
    response = answer_question("Peki kaç müşteri var?", settings, follow_up_context=context)
    expected_input = {"previous_context": context, "new_request": "Peki kaç müşteri var?"}
    expected_attempts = 2 if review_result == "unavailable" else 1
    assert calls == [(expected_input, None)] + [(expected_input, initial)] * expected_attempts
    assert response["sql_review"]["attempt_count"] == expected_attempts
    event = json.loads(settings.log_path.read_text(encoding="utf-8"))
    assert event["sql_review"] == response["sql_review"]

    if review_result == "corrected":
        assert response["status"] == "success"
        assert response["execution"]["rows"] == [[300]]
        assert response["sql_review"]["changed"]
    else:
        assert response["status"] == "error"
        assert response["execution"] is None and event["executed_sql"] is None
        assert response["error_type"] == ("sql_security" if review_result == "unsafe" else "sql_review_failed")
