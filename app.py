"""Streamlit soru ekranı; bütün sorgular güvenli servis üzerinden yürütülür."""
from collections import deque
from dataclasses import replace
import hashlib
import json
from time import perf_counter
import sqlite3
import pandas as pd
import streamlit as st
from src.analyses import ANALYSES
from src.charts import monthly_revenue_chart, result_chart
from src.config import load_settings
from src.database import QueryError
from src.sales import load_sales_filters, summarize_sales
from src.service import answer_question, run_analysis

st.set_page_config(page_title="NL2SQL Agent", page_icon=":material/analytics:", layout="wide")
st.markdown("""<style>
.block-container {max-width:1200px; padding:3rem 2.5rem 3rem;}
.stFormSubmitButton button[kind="primaryFormSubmit"]:not(:disabled) {color:#091b22; font-weight:650;}
.result-scroll {
    max-height:560px; overflow:auto; border:1px solid var(--border-color, GrayText);
    border-radius:0.75rem;
}
table.result-table {width:100%; border-collapse:collapse; text-align:left;}
table.result-table th {position:sticky; top:0; background:var(--secondary-background-color, #162238);}
table.result-table th, table.result-table td {
    padding:.65rem .85rem; border-bottom:1px solid var(--border-color, #25344b);
    white-space:nowrap;
}
table.result-table tbody tr:nth-child(even) {background:rgba(126, 161, 214, .06);}
table.result-table tbody tr:last-child td {border-bottom:0;}
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


def format_currency(value):
    number = f"{value:,.2f}".translate(str.maketrans(",.", ".,"))
    return f"{number} TL"


@st.fragment
def show_sales_overview(settings):
    with st.expander("Satış özeti", icon=":material/monitoring:"):
        try:
            filters = load_sales_filters(settings)
            if filters is None:
                st.info("Veri setinde henüz sipariş bulunmuyor.")
                return

            date_column, city_column, segment_column = st.columns([2, 1, 1])
            period = date_column.date_input(
                "Tarih aralığı", (filters.start, filters.end),
                min_value=filters.start, max_value=filters.end, format="DD.MM.YYYY", key="sales_period",
            )
            city = city_column.selectbox(
                "Şehir", (None, *filters.cities), format_func=lambda value: value or "Tüm şehirler",
                key="sales_city",
            )
            segment = segment_column.selectbox(
                "Segment", (None, *filters.segments), format_func=lambda value: value or "Tüm segmentler",
                key="sales_segment",
            )
            if len(period) != 2:
                st.caption("Özeti güncellemek için başlangıç ve bitiş tarihini seçin.")
                return
            summary = summarize_sales(settings, *period, city=city, segment=segment)
        except QueryError as error:
            st.warning(str(error))
            return
        except (OSError, sqlite3.Error, ValueError):
            st.warning("Satış özeti için veri seti okunamadı.")
            return

        revenue, orders, average = st.columns(3)
        revenue.metric("Toplam ciro", format_currency(summary.revenue), border=True)
        orders.metric("Sipariş adedi", f"{summary.order_count:,}".replace(",", "."), border=True)
        average_value = summary.average_order_value
        average.metric(
            "Ortalama sepet tutarı", format_currency(average_value) if average_value is not None else "—",
            help="Seçili dönemdeki toplam cironun sipariş adedine bölümü.", border=True,
        )
        if not summary.order_count:
            st.info("Seçili filtrelere uyan sipariş bulunamadı.")
            return
        st.markdown("#### Aylık ciro")
        st.altair_chart(monthly_revenue_chart(summary.monthly_revenue), width="stretch", key="sales_revenue_chart")


database_ready = settings.database_path.is_file()
model_ready = bool(settings.gemini_api_key and settings.gemini_model)
ready = database_ready and model_ready
if not database_ready:
    st.warning("Veri seti bulunamadı. Önce veri yükleme adımını tamamlayın.")
else:
    show_sales_overview(settings)
if not model_ready:
    st.warning("Serbest soru sormak için .env dosyasında Gemini bağlantısını yapılandırın.")

previous = st.session_state.get("last_answer")
can_follow_up = previous and previous["response"]["status"] in {"success", "empty", "clarification"}
with st.form("question_form"):
    question_area, model_area = st.columns([3, 1])
    with question_area:
        question = st.text_area(
            "Satış verileri hakkında sorunuzu yazın", placeholder="Örnek: En yüksek ciroya sahip 5 ürün hangisi?",
            max_chars=4000, key="question_input", height=110,
        )
    with model_area:
        st.selectbox("Model", [settings.gemini_model or "Gemini"], disabled=True, key="question_model")
        st.caption("Model seçimi · Coming soon!")

    follow_up = False
    with st.container(horizontal=True):
        submitted = st.form_submit_button("Sorgula", disabled=not ready, type="primary", icon=":material/search:")
        if can_follow_up:
            follow_up = st.form_submit_button("Önceki soruya bağlı sorgula", disabled=not ready)

with st.expander("Örnek sorular"):
    st.caption("Bir örnek seçin, ardından soru alanında düzenleyip sorgulayın.")
    for index, text in enumerate(PRESET_QUESTIONS):
        st.button(text, key=f"preset_{index}", on_click=fill_question, args=(text,))

st.subheader("Hazır analizler")
st.caption("Satış veri setinin tamamında tek tıklamayla çalıştırın.")
selected_analysis = None
for (key, analysis), column in zip(ANALYSES.items(), st.columns(len(ANALYSES))):
    with column.container(border=True):
        if st.button(analysis.title, key=f"analysis_{key}", icon=analysis.icon,
                     disabled=not database_ready, width="stretch"):
            selected_analysis = key
        st.caption(analysis.description)

if selected_analysis:
    analysis = ANALYSES[selected_analysis]
    with st.spinner(f"{analysis.title} çalışıyor…"):
        response = run_analysis(selected_analysis, settings)
    st.session_state["last_answer"] = {
        "question": analysis.title, "response": response, "context": [],
        "duration_ms": response["duration_ms"], "analysis_key": selected_analysis,
    }
    st.rerun()

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
    retries = f" · Yeniden deneme {response.get('retry_count', 0)}" if not saved.get("analysis_key") else ""
    st.caption(f"{names.get(status, status)} · Toplam süre {saved['duration_ms']/1000:.2f} sn{retries}")
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
        chart, chart_note = result_chart(frame, saved.get("analysis_key"))
        if chart is not None:
            with st.container(border=True):
                st.markdown("#### Sonuç grafiği")
                st.altair_chart(chart, width="stretch")
                if chart_note:
                    st.caption(chart_note)
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
    sql = response.get("analysis_sql") or generation.get("result", {}).get("sql")
    if sql:
        label = "Hazır analiz SQL’ini incele" if saved.get("analysis_key") else "Üretilen SQL’i incele"
        with st.expander(label, expanded=False):
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
