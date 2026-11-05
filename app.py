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
/* Renkler Streamlit temasından miras alınır; light/dark zorlanmaz. */
.stApp {background-image:linear-gradient(145deg,#8cb6d00a,#7da8c42b);}

.block-container {max-width:1500px; padding:2.8rem 3.5rem 4rem;}
p, li, label, [data-testid="stMarkdownContainer"] p {font-size:20px; line-height:1.65;}
[data-testid="stCaptionContainer"] p {font-size:17px; color:inherit;opacity:.8;}
h1,h2,h3 {color:inherit; letter-spacing:-.035em;}
h2 {font-size:32px !important;}
h3 {font-size:27px !important;}
.hero {padding:40px 44px; border:1px solid #c8dce8; border-radius:26px;
background:linear-gradient(110deg,#94bcd216,#7ea9c43d); margin-bottom:28px; box-shadow:0 12px 40px #335c7610;}
.hero .eyebrow {font-size:15px;letter-spacing:3px;color:inherit;opacity:.75;font-weight:700;}
.hero h1 {color:inherit;font-size:64px;line-height:1.1;margin:14px 0 18px;}
.hero p {color:inherit;opacity:.85;font-size:23px;max-width:950px;margin:0;}
div[data-testid="stForm"] {background:color-mix(in srgb,currentColor 5%,transparent);border-radius:22px;padding:32px;border:1px solid #c8dce8;box-shadow:0 8px 24px #335c7608;}
[data-testid="stTextArea"] textarea {color:inherit !important;-webkit-text-fill-color:currentColor;font-size:23px !important;line-height:1.65;min-height:190px;border-radius:14px;}
[data-testid="stTextArea"] label, [data-testid="stTextArea"] label p,
[data-testid="stTextArea"] [data-testid="stWidgetLabel"] p {color:inherit !important;font-size:22px;font-weight:700;}
[data-testid="stTextArea"] textarea::placeholder {color:inherit !important;opacity:.65;-webkit-text-fill-color:currentColor;}
[data-testid="stMarkdownContainer"] p, [data-testid="stMetricLabel"] p {color:inherit;}
[data-testid="stAlert"] p {color:inherit;}
.stButton button {background:color-mix(in srgb,currentColor 4%,transparent);border:1px solid #bdd4e3;border-radius:15px;min-height:88px;padding:16px 20px;width:100%;}
.stButton button p {font-size:18px !important;line-height:1.4;text-align:left;}
.stButton button:hover {background:#7da9c426;border-color:#7da9c6;}
.stFormSubmitButton button {background:#315f7c;border:1px solid #315f7c;color:#fff;border-radius:13px;min-height:58px;padding:12px 36px;}
.stFormSubmitButton button p {font-size:21px !important;font-weight:600;color:#fff !important;}
.stFormSubmitButton button:hover {background:#254b65;border-color:#254b65;color:#fff;}
[data-testid="stMetric"] {background:color-mix(in srgb,currentColor 5%,transparent);border:1px solid #9ebbd0;padding:22px;border-radius:18px;}
[data-testid="stMetricLabel"] p {font-size:18px;}
[data-testid="stMetricValue"] {font-size:34px;color:inherit;}
[data-testid="stExpander"] {background:color-mix(in srgb,currentColor 4%,transparent);border:1px solid #c8dce8;border-radius:16px;}
[data-testid="stExpander"] summary p {font-size:20px;}
[data-testid="stCode"] code {font-size:20px;}
.result-scroll {max-height:620px;overflow:auto;border:1px solid #9ebbd0;border-radius:16px;margin:20px 0;}
table.result-table {width:100%;border-collapse:collapse;font-size:24px;line-height:1.6;text-align:left;}
table.result-table th {font-size:21px;font-weight:700;position:sticky;top:0;background:var(--background-color,Canvas);z-index:1;}
table.result-table th, table.result-table td {padding:20px 26px;border-bottom:1px solid #8cabb744;white-space:nowrap;color:inherit;}
table.result-table tbody tr:nth-child(odd) {background:#7da9c416;}
@media(max-width:768px) {table.result-table {font-size:20px;}table.result-table th,table.result-table td {padding:16px;}}
@media(max-width:768px) {
.block-container {padding:1.5rem 1rem 3rem;}
.hero {padding:28px 22px;}
.hero h1 {font-size:42px;}
.hero p {font-size:20px;}
div[data-testid="stForm"] {padding:20px;}
}
</style>
<div class="hero"><div class="eyebrow">DOĞAL DİLDEN VERİYE</div>
<h1>NL2SQL Agent</h1><p>Satışlar, müşteriler ve ürünler hakkında sorunuzu yazın.<br>Verilerinizi anlaşılır sonuçlara dönüştürün.</p></div>""", unsafe_allow_html=True)
try:
    settings = replace(load_settings(), review_sql=True)
except ValueError:
    st.error("Yapılandırma geçersiz. Ortam ayarlarını kontrol edin.")
    st.stop()

st.caption(f"Hızlı tüketim (FMCG) örnek satış verileri · Referans tarihi: {settings.reference_date.isoformat()} · Sonuç sınırı: {settings.max_result_rows} satır")
st.subheader("Hazır sorular")
st.caption("Bir soruya tıklayın; metni aşağıdaki alanda düzenleyip sorgulayın.")
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


for offset in range(0, len(PRESET_QUESTIONS), 3):
    columns = st.columns(3)
    for index, text in enumerate(PRESET_QUESTIONS[offset:offset+3]):
        columns[index].button(text, key=f"preset_{offset+index}", on_click=fill_question, args=(text,), width="stretch")
st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
ready = settings.database_path.is_file() and bool(settings.gemini_api_key and settings.gemini_model)
if not settings.database_path.is_file():
    st.warning("Veri seti bulunamadı. Önce veri yükleme adımını tamamlayın.")
if not settings.gemini_api_key or not settings.gemini_model:
    st.warning("Gemini bağlantısı yapılandırılmamış. .env ayarlarını tamamlayın.")

previous = st.session_state.get("last_answer")
can_follow_up = previous and previous["response"]["status"] in {"success", "empty", "clarification"}
with st.form("question_form"):
    question = st.text_area("İş sorunuzu yazın", placeholder="Örnek: En yüksek ciroya sahip 5 ürün hangisi?", max_chars=4000, key="question_input", height=210)
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
    st.caption(f"Durum: {names.get(status, status)} · Toplam süre: {saved['duration_ms']/1000:.2f} sn")
    metrics = st.columns(3)
    metrics[0].metric("Toplam süre", f"{saved['duration_ms']/1000:.2f} sn")
    metrics[1].metric("Sonuç satırı", (response.get("execution") or {}).get("row_count", 0))
    metrics[2].metric("Yeniden deneme", response.get("retry_count", 0))
    if response.get("retry_count"):
        st.caption("Geçici model hatasından sonra bir kez yeniden denendi.")
    if response.get("log_warning"):
        st.warning(response["log_warning"])
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
    execution = response.get("execution")
    if status == "success" and execution:
        st.success("Sorgu tamamlandı.")
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
