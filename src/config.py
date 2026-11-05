"""Uygulama yapılandırması; yollar proje köküne göre çözülür."""
import os
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    database_path: Path
    reference_date: date
    gemini_api_key: str = field(repr=False)
    gemini_model: str
    model_timeout_seconds: float
    query_timeout_seconds: float
    max_result_rows: int
    log_path: Path = ROOT / "reports/events.jsonl"
    review_sql: bool = False


def load_settings() -> Settings:
    load_dotenv(ROOT / ".env", override=False)
    path = Path(os.getenv("DATABASE_PATH", "data/analytics.db"))
    reference = date.fromisoformat(os.getenv("REFERENCE_DATE", "2026-06-30"))
    if reference != date(2026, 6, 30):
        raise ValueError("Ödev için referans tarihi 2026-06-30 olmalıdır.")
    model_timeout = float(os.getenv("MODEL_TIMEOUT_SECONDS", "60"))
    query_timeout = float(os.getenv("QUERY_TIMEOUT_SECONDS", "5"))
    rows = int(os.getenv("MAX_RESULT_ROWS", "500"))
    if not all(math.isfinite(t) and t > 0 for t in (model_timeout, query_timeout)) or not 1 <= rows <= 500:
        raise ValueError("Süre sınırları pozitif, satır sınırı 1-500 olmalıdır.")
    return Settings(
        database_path=path if path.is_absolute() else ROOT / path,
        reference_date=reference,
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip().removeprefix("models/"),
        model_timeout_seconds=model_timeout,
        query_timeout_seconds=query_timeout,
        max_result_rows=rows,
        log_path=ROOT / os.getenv("LOG_PATH", "reports/events.jsonl"),
    )
