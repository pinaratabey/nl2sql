"""Güvenli sorgu akışı, model turu başına en fazla bir geçici hata tekrarı ve JSONL olay kaydı."""
import json
import sqlite3
from datetime import datetime
from time import perf_counter
from uuid import uuid4
from zoneinfo import ZoneInfo
from src.config import load_settings
from src.database import execute_query, QueryError
from src.llm import generate_sql, ModelError
from src.sql_security import SQLSecurityError

TRANSIENT_ERRORS = {"model_timeout", "model_unavailable"}


def answer_question(question: str, settings=None, *, follow_up_context=None) -> dict:
    settings = settings or load_settings()
    started = perf_counter()
    request_id = str(uuid4())
    generated = None
    attempts = []
    model_duration = 0.0
    response = None
    review = None
    if not isinstance(question, str) or not question.strip() or len(question) > 4000:
        response = {"status":"error", "error_type":"input", "message":"1-4000 karakter uzunluğunda bir soru yazın."}
    else:
        model_question = question.strip()
        if follow_up_context:
            model_question = json.dumps({"previous_context": follow_up_context, "new_request": model_question}, ensure_ascii=False)
        for attempt in range(2):
            attempt_started = perf_counter()
            try:
                generated = generate_sql(model_question, settings)
            except ModelError as error:
                elapsed = (perf_counter()-attempt_started)*1000
                model_duration += elapsed
                attempts.append({"attempt":attempt+1, "status":"error", "error_type":error.error_type, "duration_ms":round(elapsed)})
                if attempt == 0 and error.error_type in TRANSIENT_ERRORS:
                    continue
                messages = {
                    "model_timeout":"Gemini zamanında yanıt vermedi. Lütfen daha sonra yeniden deneyin.",
                    "model_unavailable":"Gemini bağlantısı kurulamadı. İnternet bağlantınızı kontrol edin.",
                    "rate_limit":"Gemini kullanım kotasına ulaşıldı. Kota yenilendiğinde tekrar deneyin.",
                    "authentication":"Gemini anahtarı doğrulanamadı. Bağlantı ayarlarını kontrol edin.",
                    "access_denied":"Bu Gemini modeline erişim izni yok.",
                    "model_not_found":"Seçilen Gemini modeli bulunamadı.",
                }
                response = {"status":"error", "error_type":error.error_type, "message":messages.get(error.error_type,str(error)),
                            "response_diagnostic":getattr(error,"response_diagnostic",None)}
                break
            except (OSError, sqlite3.Error, ValueError):
                response = {"status":"error", "error_type":"database_unavailable", "message":"Veri seti veya şema okunamadı. Veri yüklemesini kontrol edin."}
                attempts.append({"attempt":attempt+1,"status":"error","error_type":"database_unavailable","duration_ms":round((perf_counter()-attempt_started)*1000)})
                break
            elapsed = (perf_counter()-attempt_started)*1000
            model_duration += elapsed
            attempts.append({"attempt":attempt+1,"status":"success","error_type":None,"duration_ms":round(elapsed)})
            result = generated["result"]
            if result["status"] != "ok":
                response = {"status":result["status"], "message":result["message"]}
                break
            if settings.review_sql:
                review_started = perf_counter()
                review_attempts = []
                for review_attempt in range(2):
                    try:
                        reviewed = generate_sql(model_question, settings, candidate_sql=result["sql"])
                    except ModelError as error:
                        review_attempts.append(error.error_type)
                        if review_attempt == 0 and error.error_type in TRANSIENT_ERRORS:
                            continue
                        response = {"status": "error", "error_type": "sql_review_failed",
                                    "message": "SQL kontrolü tamamlanamadı. Sorgu çalıştırılmadı."}
                    except (OSError, sqlite3.Error, ValueError):
                        review_attempts.append("database_unavailable")
                        response = {"status": "error", "error_type": "database_unavailable",
                                    "message": "SQL kontrolü sırasında veri şeması okunamadı."}
                    else:
                        review_attempts.append(None)
                    break
                review_duration = (perf_counter() - review_started) * 1000
                model_duration += review_duration
                review = {
                    "duration_ms": round(review_duration),
                    "attempt_count": len(review_attempts),
                    "retry_count": len(review_attempts) - 1,
                    "attempt_errors": review_attempts,
                    "initial_sql": result["sql"],
                }
                if response is not None:
                    review.update(status="error", error_type=review_attempts[-1])
                    break
                checked_result = reviewed["result"]
                review.update(
                    status=checked_result["status"],
                    changed=checked_result.get("sql") != result["sql"],
                    checked_sql=checked_result.get("sql"),
                )
                generated = reviewed
                if checked_result["status"] != "ok":
                    response = {"status": checked_result["status"], "message": checked_result["message"]}
                    break
                result = checked_result
            try:
                execution = execute_query(result["sql"],settings.database_path,settings.query_timeout_seconds,settings.max_result_rows)
                generated["sql_executed"] = True
                response = {"status":"success" if execution["rows"] else "empty", "execution":execution,
                            "message":"Sonuçlar hazır." if execution["rows"] else "Sorgu kayıt döndürmedi."}
            except (QueryError, SQLSecurityError) as error:
                response = {"status":"error", "error_type":getattr(error,"error_type","sql_security"), "message":str(error)}
            except (OSError, sqlite3.Error, ValueError):
                response = {"status":"error", "error_type":"database_unavailable", "message":"Veri setine erişilemiyor. Veri yüklemesini kontrol edin."}
            break  # SQL/güvenlik hatası tekrar denenmez.
    response.setdefault("execution",None)
    response.setdefault("error_type",None)
    response["generation"] = generated
    response["sql_review"] = review
    response.update(request_id=request_id, attempt_count=len(attempts), retry_count=max(0,len(attempts)-1),
                    duration_ms=round((perf_counter()-started)*1000), model_duration_ms=round(model_duration))
    execution = response["execution"] or {}
    event = {"request_id":request_id,"timestamp":datetime.now(ZoneInfo("Europe/Istanbul")).isoformat(),
             "question":question,"generated_sql":(generated or {}).get("result",{}).get("sql"),
             "executed_sql":execution.get("executed_sql"),"status":response["status"],"error_type":response["error_type"],
             "duration_ms":response["duration_ms"],"model_duration_ms":response["model_duration_ms"],
             "execution_duration_ms":execution.get("duration_ms"),"attempt_count":len(attempts),"attempts":attempts,
             "retry_count":response["retry_count"],"sql_review":review,"row_count":execution.get("row_count",0),"truncated":execution.get("truncated",False),
             "model_id":settings.gemini_model,"reference_date":settings.reference_date.isoformat()}
    try:
        serialized = json.dumps(event,ensure_ascii=False)
        if settings.gemini_api_key:
            serialized = serialized.replace(settings.gemini_api_key,"[REDACTED]")
        settings.log_path.parent.mkdir(parents=True,exist_ok=True)
        with settings.log_path.open("a",encoding="utf-8") as stream:
            stream.write(serialized+"\n")
    except OSError:
        # Sorguyu yeniden çalıştırma: sadece kayıt hatasını kullanıcıya bildir.
        response["log_warning"] = "İstek tamamlandı ancak olay kaydı yazılamadı. Kayıt klasörünü kontrol edin."
    return response
