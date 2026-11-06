"""Streamlit soru ekranı; bütün sorgular güvenli servis üzerinden yürütülür."""
from collections import deque
from dataclasses import replace
import hashlib
import json
from time import perf_counter
import sqlite3
import pandas as pd
import streamlit as st
from src.config import load_settings
from src.service import answer_question

st.set_page_config(page_title="NL2SQL Agent", layout="wide")
st.markdown("""<style>
.block-container {max-width:1160px; padding:2.5rem 2rem 3rem;}
.stFormSubmitButton button[kind="primaryFormSubmit"]:not(:disabled) {color:#000;}
.result-scroll {max-height:620px; overflow:auto; border:1px solid var(--border-color, GrayText);}
table.result-table {width:100%; border-collapse:collapse; text-align:left;}
table.result-table th {position:sticky; top:0; background:var(--secondary-background-color, #464545);}
table.result-table th, table.result-table td {
    padding:.65rem .85rem; border-bottom:1px solid var(--border-color, #464545);
    white-space:nowrap;
}
@media(max-width:768px) {
    .block-container {padding:1.5rem 1rem 2rem;}
}
</style>""", unsafe_allow_html=True)
st.title("NL2SQL Agent")
st.write("Hızlı tüketim verilerinde satışları, müşterileri ve ürünleri Türkçe sorularla analiz edin.")
try:
    settings = replace(load_settings(), review_sql=True)
except ValueError:
    st.error("Yapılandırma geçersiz. Ortam ayarlarını kontrol edin.")
    st.stop()

st.caption(f"Referans tarihi: {settings.reference_date.isoformat()} · Sonuç sınırı: {settings.max_result_rows} satır")
PRESET_QUESTIONS = [
    "En yüksek ciroya sahip 5 ürün hangisi?",
    "İzmir'in toplam cirosu nedir?",
    "Son 6 ayın aylık ciro trendi nedir?",
    "Kategori bazında ortalama sipariş kalemi tutarı nedir?",
    "Hiç sipariş vermemiş müşteriler kimler?",
    "Segmentlere göre ciro karşılaştırması nedir?",
]


def fill_question(text):
    st.session_state["question_input"] = text


with st.expander("Örnek sorular"):
    st.caption("Bir örnek seçin, ardından soru alanında düzenleyip sorgulayın.")
    for index, text in enumerate(PRESET_QUESTIONS):
        st.button(text, key=f"preset_{index}", on_click=fill_question, args=(text,))

ready = settings.database_path.is_file() and bool(settings.gemini_api_key and settings.gemini_model)
if not settings.database_path.is_file():
    st.warning("Veri seti bulunamadı. Önce veri yükleme adımını tamamlayın.")
if not settings.gemini_api_key or not settings.gemini_model:
    st.warning("Gemini bağlantısı yapılandırılmamış. .env ayarlarını tamamlayın.")

previous = st.session_state.get("last_answer")
can_follow_up = previous and previous["response"]["status"] in {"success", "empty", "clarification"}
with st.form("question_form"):
    question = st.text_area("Satış verileri hakkında sorunuzu yazın", placeholder="Örnek: En yüksek ciroya sahip 5 ürün hangisi?", max_chars=4000, key="question_input", height=120)
    submitted = st.form_submit_button("Sorgula", disabled=not ready, type="primary")

    follow_up = False
    if can_follow_up:
        follow_up = st.form_submit_button("Önceki soruya bağlı sorgula", disabled=not ready)

if submitted or follow_up:
    st.session_state.pop("last_answer", None)
    if not question.strip():
        st.warning("Lütfen bir soru yazın.")
    else:
        started = perf_counter()
        context = []
        with st.spinner("Sorunuz değerlendiriliyor…"):
            try:
                if follow_up:
                    turn = {"question": previous["question"]}
                    previous_response = previous["response"]
                    if previous_response["status"] == "clarification":
                        turn["clarification"] = previous_response["message"]
                    elif (previous_response.get("execution") or {}).get("validated_sql"):
                        turn["sql"] = previous_response["execution"]["validated_sql"]
                    context = [*previous.get("context", []), turn][-3:]
                    response = answer_question(question.strip(), settings, follow_up_context=context)
                else:
                    response = answer_question(question.strip(), settings)
            except (OSError, sqlite3.Error):
                response = {"status":"error", "error_type":"database_unavailable", "message":"Veri setine erişilemiyor. Veri yükleme ve dosya izinlerini kontrol edin.", "generation":None, "execution":None}
        st.session_state["last_answer"] = {"question":question.strip(), "response":response, "context":context, "duration_ms":round((perf_counter()-started)*1000)}
        st.rerun()

saved = st.session_state.get("last_answer")
if saved:
    response = saved["response"]
    st.divider()
    st.subheader("Analiz sonucu")
    st.write(saved["question"])
    status = response["status"]
    names = {"success":"Başarılı", "empty":"Boş sonuç", "clarification":"Açıklama gerekiyor", "rejected":"İstek reddedildi", "error":"Hata"}
    st.caption(f"{names.get(status, status)} · Toplam süre {saved['duration_ms']/1000:.2f} sn · Yeniden deneme {response.get('retry_count', 0)}")
    if response.get("retry_count"):
        st.caption("Geçici model hatasından sonra bir kez yeniden denendi.")
    if response.get("log_warning"):
        st.warning(response["log_warning"])
    execution = response.get("execution")
    if status == "success" and execution:
        # Aynı adlı SELECT sütunları da tabloya güvenle aktarılır.
        labels, used = [], set()
        for name in execution["columns"]:
            label, suffix = name, 2
            while label in used:
                label = f"{name} ({suffix})"
                suffix += 1
            used.add(label)
            labels.append(label)
        frame = pd.DataFrame(execution["rows"], columns=labels)
        # İçerik HTML olarak kaçırılır; veri/SQL bir HTML talimatına dönüşmez.
        table_html = frame.to_html(index=False, escape=True, classes="result-table", border=0)
        st.markdown(f'<div class="result-scroll">{table_html}</div>', unsafe_allow_html=True)
        with st.expander("Etkileşimli tabloyu aç"):
            st.dataframe(frame, hide_index=True, width="stretch", row_height=52, height=min(620, 60 + 52 * max(1, len(frame))))
        # Elektronik tablo uygulamalarının metni formül olarak yorumlamasını önle.
        def csv_cell(value):
            if isinstance(value, str) and (
                value.startswith(("\t", "\r", "\n")) or value.lstrip().startswith(("=", "+", "-", "@"))
            ):
                return "'" + value
            return value

        csv_frame = frame.map(csv_cell).rename(columns=csv_cell)
        st.download_button("CSV indir", csv_frame.to_csv(index=False).encode("utf-8-sig"),
                           file_name="nl2sql-sonuc.csv", mime="text/csv", on_click="ignore")
        st.caption(f"{execution['row_count']} satır · Sorgu süresi: {execution['duration_ms']} ms")
        if execution.get("truncated"):
            st.warning(f"Sonuç sınırı nedeniyle ilk {settings.max_result_rows} satır gösteriliyor.")
    elif status == "empty":
        st.info("Sorgu başarıyla çalıştı; eşleşen kayıt bulunamadı.")
    elif status == "clarification":
        st.info(response["message"])
    elif status == "rejected":
        st.warning(response["message"])
    else:
        st.error(response.get("message", "İstek tamamlanamadı."))
        if response.get("error_type"):
            st.caption(f"Hata türü: {response['error_type']}")

    generation = response.get("generation") or {}
    sql = generation.get("result", {}).get("sql")
    if sql:
        with st.expander("Üretilen SQL’i incele", expanded=False):
            st.code(sql, language="sql")
    review = response.get("sql_review")
    if review:
        with st.expander("İkinci tur SQL kontrolü"):
            st.caption(f"Kontrol süresi · {review['duration_ms']} ms · Yeniden deneme: {review.get('retry_count', 0)}")
            if review["status"] == "ok":
                st.write("SQL düzeltildi." if review["changed"] else "Aday SQL onaylandı.")
                if review["changed"]:
                    st.code(review["initial_sql"], language="sql")
            else:
                st.write(response["message"])


st.divider()
if st.toggle("Sorgu loglarını göster"):
    st.subheader("Sorgu logları")
    try:
        with settings.log_path.open(encoding="utf-8") as stream:
            recent = deque(stream, maxlen=200)
    except FileNotFoundError:
        recent = []
    except (OSError, UnicodeError):
        recent = []
        st.warning("Log dosyası okunamadı.")

    events = []
    raw_events = []
    for line in reversed(recent):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            raw_events.append(event)
            events.append({
                "Zaman": event.get("timestamp"),
                "İstek kimliği": event.get("request_id"),
                "Soru": event.get("question"),
                "Durum": event.get("status"),
                "Hata": event.get("error_type"),
                "Süre (ms)": event.get("duration_ms"),
                "Satır": event.get("row_count"),
                "Yeniden deneme": event.get("retry_count"),
                "SQL kontrolü": (event.get("sql_review") or {}).get("status"),
                "Yürütülen SQL": event.get("executed_sql"),
            })
    if events:
        statuses = sorted({event["Durum"] for event in events if isinstance(event["Durum"], str)})
        def reset_log_page():
            st.session_state["log_page"] = 1

        status_filter = st.multiselect("Duruma göre filtrele", statuses, on_change=reset_log_page)
        visible_indices = [
            index for index, event in enumerate(events)
            if not status_filter or event["Durum"] in status_filter
        ]
        page_size = 10
        page_count = max(1, (len(visible_indices) + page_size - 1) // page_size)
        if st.session_state.get("log_page", 1) > page_count:
            st.session_state["log_page"] = 1
        page = st.number_input("Log sayfası", min_value=1, max_value=page_count,
                               step=1, key="log_page", disabled=page_count == 1)
        start = (page - 1) * page_size
        page_indices = visible_indices[start:start + page_size]
        st.caption(f"Sayfa {page}/{page_count} · Bu sayfada {len(page_indices)} kayıt · Filtreye uyan {len(visible_indices)} kayıt")
        st.dataframe(pd.DataFrame([events[index] for index in page_indices]), hide_index=True, width="stretch")

        by_request = {
            events[index]["İstek kimliği"] or hashlib.sha256(
                json.dumps(raw_events[index], sort_keys=True).encode("utf-8")
            ).hexdigest(): index
            for index in visible_indices
        }

        def log_label(option):
            index = by_request[option]
            event = events[index]
            question = " ".join(str(event["Soru"] or "").split())[:100]
            return f"{index + 1}. {event['Zaman'] or 'Tarih yok'} · {event['Durum'] or 'Durum yok'} · {question}"

        selected = st.multiselect("İndirilecek logları seç", list(by_request), format_func=log_label)
        if selected:
            payload = json.dumps([raw_events[by_request[option]] for option in selected], ensure_ascii=False, indent=2)
            st.download_button("Seçili logları indir", payload + "\n", file_name="nl2sql-loglar.json",
                               mime="application/json", on_click="ignore")
    else:
        st.info("Görüntülenecek sorgu kaydı bulunamadı.")
