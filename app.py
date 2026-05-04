import plotly.express as px
import streamlit as st

from src.chatbot import answer_question, answer_question_with_llm
from src.config import DUCKDB_PATH
from src.insights import generate_insights, generate_markdown_report
from src.queries import (
    compare_zone_type,
    get_filter_options,
    get_overview,
    high_low_multivariable,
    metric_trend,
    sample_rows,
    top_zones_by_metric,
)


st.set_page_config(
    page_title="Rappi AI Ops Assistant",
    page_icon="R",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def cached_overview():
    return get_overview()


@st.cache_data(show_spinner=False)
def cached_filter_options():
    return get_filter_options()


@st.cache_data(show_spinner=False)
def cached_insights():
    sections = generate_insights()
    report = generate_markdown_report(sections)
    return sections, report


st.title("Rappi AI Ops Assistant")
st.caption("Analisis conversacional e insights operacionales sobre metricas por zona.")

if not DUCKDB_PATH.exists():
    st.error("La base DuckDB no existe. Ejecuta `python scripts/build_database.py` primero.")
    st.stop()

overview = cached_overview().iloc[0]
options = cached_filter_options()

metric_cols = st.columns(6)
metric_cols[0].metric("Filas", f"{int(overview['rows']):,}")
metric_cols[1].metric("Paises", f"{int(overview['countries']):,}")
metric_cols[2].metric("Ciudades", f"{int(overview['cities']):,}")
metric_cols[3].metric("Zonas", f"{int(overview['zones']):,}")
metric_cols[4].metric("Metricas", f"{int(overview['metrics']):,}")
metric_cols[5].metric("Match ordenes", f"{overview['order_match_rate_pct']:.2f}%")

tab_chat, tab_insights, tab_top, tab_compare, tab_trend, tab_multi, tab_data = st.tabs(
    [
        "Bot",
        "Insights",
        "Top zonas",
        "Comparaciones",
        "Tendencias",
        "Multivariable",
        "Datos",
    ]
)

with tab_chat:
    st.subheader("Bot conversacional de datos")

    examples = [
        "Cuales son las 5 zonas con mayor Lead Penetration esta semana?",
        "Compara el Perfect Orders entre zonas Wealthy y Non Wealthy en Mexico",
        "Muestra la evolucion de Gross Profit UE en Chapinero ultimas 8 semanas",
        "Que zonas tienen alto Lead Penetration pero bajo Perfect Orders?",
        "Cuales son las zonas que mas crecen en ordenes en las ultimas 5 semanas?",
    ]

    selected_example = st.selectbox("Preguntas sugeridas", examples)
    bot_mode = st.radio(
        "Modo de respuesta",
        ["Deterministico", "LLM + guardrails"],
        horizontal=True,
        help="El modo LLM interpreta la pregunta con OpenAI, pero la consulta SQL sigue controlada por la aplicacion.",
    )
    question = st.text_input("Pregunta", value=selected_example)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if st.button("Preguntar", type="primary"):
        if bot_mode == "LLM + guardrails":
            response = answer_question_with_llm(question)
        else:
            response = answer_question(question)
        st.session_state.chat_history.append((question, response))

    for user_question, response in reversed(st.session_state.chat_history[-5:]):
        with st.chat_message("user"):
            st.write(user_question)

        with st.chat_message("assistant"):
            st.write(response.answer)
            st.dataframe(response.data, use_container_width=True, hide_index=True)

            if response.chart_type == "bar" and not response.data.empty:
                numeric_cols = response.data.select_dtypes(include="number").columns.tolist()
                y_col = numeric_cols[0] if numeric_cols else None
                x_col = "ZONE" if "ZONE" in response.data.columns else response.data.columns[0]
                if y_col:
                    color_col = "COUNTRY" if "COUNTRY" in response.data.columns else None
                    fig = px.bar(response.data, x=x_col, y=y_col, color=color_col)
                    st.plotly_chart(fig, use_container_width=True)

            if response.chart_type == "line" and not response.data.empty:
                fig = px.line(
                    response.data.sort_values("WEEK_LAG", ascending=False),
                    x="WEEK_LAG",
                    y="metric_value",
                    markers=True,
                )
                st.plotly_chart(fig, use_container_width=True)

            if response.chart_type == "scatter" and not response.data.empty:
                if {"lead_penetration", "perfect_orders", "orders"}.issubset(response.data.columns):
                    fig = px.scatter(
                        response.data,
                        x="lead_penetration",
                        y="perfect_orders",
                        size="orders",
                        color="COUNTRY",
                        hover_data=["CITY", "ZONE", "ZONE_TYPE"],
                    )
                    st.plotly_chart(fig, use_container_width=True)

            if response.followups:
                st.caption("Sugerencias de seguimiento")
                for followup in response.followups:
                    st.write(f"- {followup}")

            with st.expander("Ver SQL ejecutado"):
                st.code(response.sql, language="sql")

with tab_insights:
    st.subheader("Insights automaticos")
    st.write("Hallazgos generados con reglas reproducibles sobre la tabla SQL local.")

    if st.button("Generar insights", type="primary"):
        st.cache_data.clear()

    insight_sections, markdown_report = cached_insights()

    st.download_button(
        "Descargar reporte Markdown",
        data=markdown_report,
        file_name="executive_report.md",
        mime="text/markdown",
    )

    for section in insight_sections:
        with st.expander(section.title, expanded=True):
            st.write(section.description)
            st.info(section.recommendation)
            if section.data.empty:
                st.warning("No se encontraron casos para esta categoria.")
            else:
                st.dataframe(section.data, use_container_width=True, hide_index=True)

with tab_top:
    st.subheader("Top zonas por metrica")
    col_a, col_b, col_c = st.columns([2, 2, 1])
    selected_metric = col_a.selectbox("Metrica", options["metrics"], index=options["metrics"].index("Lead Penetration"))
    selected_country = col_b.selectbox("Pais", ["Todos"] + options["countries"])
    selected_week = col_c.selectbox("Semana", list(range(0, 9)), index=0, format_func=lambda value: f"L{value}W")

    top_df = top_zones_by_metric(
        metric=selected_metric,
        country=None if selected_country == "Todos" else selected_country,
        week_lag=selected_week,
        limit=10,
    )

    st.dataframe(top_df, use_container_width=True, hide_index=True)

    if not top_df.empty:
        fig = px.bar(
            top_df.sort_values("METRIC_VALUE"),
            x="METRIC_VALUE",
            y="ZONE",
            color="COUNTRY",
            orientation="h",
            hover_data=["CITY", "ZONE_TYPE", "ORDERS_VALUE"],
            title=f"Top zonas por {selected_metric}",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab_compare:
    st.subheader("Comparacion por tipo de zona")
    col_a, col_b, col_c = st.columns([2, 2, 1])
    compare_metric = col_a.selectbox("Metrica", options["metrics"], index=options["metrics"].index("Perfect Orders"), key="compare_metric")
    compare_country = col_b.selectbox("Pais", options["countries"], index=options["countries"].index("Mexico"), key="compare_country")
    compare_week = col_c.selectbox("Semana", list(range(0, 9)), index=0, format_func=lambda value: f"L{value}W", key="compare_week")

    compare_df = compare_zone_type(compare_metric, compare_country, compare_week)
    st.dataframe(compare_df, use_container_width=True, hide_index=True)

    if not compare_df.empty:
        fig = px.bar(
            compare_df,
            x="ZONE_TYPE",
            y="avg_metric_value",
            color="ZONE_TYPE",
            text_auto=True,
            title=f"{compare_metric} por tipo de zona en {compare_country}",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab_trend:
    st.subheader("Tendencia temporal por zona")
    col_a, col_b, col_c, col_d = st.columns(4)
    trend_metric = col_a.selectbox("Metrica", options["metrics"], index=options["metrics"].index("Gross Profit UE"), key="trend_metric")
    trend_country = col_b.text_input("Pais", value="Colombia")
    trend_city = col_c.text_input("Ciudad", value="Bogota")
    trend_zone = col_d.text_input("Zona", value="Chapinero")

    trend_df = metric_trend(trend_metric, trend_country, trend_city, trend_zone)
    st.dataframe(trend_df, use_container_width=True, hide_index=True)

    if not trend_df.empty:
        chart_df = trend_df.sort_values("WEEK_LAG", ascending=False)
        chart_df["WEEK"] = chart_df["WEEK_LAG"].apply(lambda value: f"L{value}W")
        fig = px.line(
            chart_df,
            x="WEEK",
            y="METRIC_VALUE",
            markers=True,
            title=f"Evolucion de {trend_metric} en {trend_zone}",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab_multi:
    st.subheader("Analisis multivariable")
    col_a, col_b = st.columns(2)
    high_metric = col_a.selectbox("Metrica alta", options["metrics"], index=options["metrics"].index("Lead Penetration"))
    low_metric = col_b.selectbox("Metrica baja", options["metrics"], index=options["metrics"].index("Perfect Orders"))
    col_c, col_d, col_e = st.columns(3)
    high_threshold = col_c.number_input("Umbral alto", value=0.70)
    low_threshold = col_d.number_input("Umbral bajo", value=0.80)
    multi_week = col_e.selectbox("Semana", list(range(0, 9)), index=0, format_func=lambda value: f"L{value}W", key="multi_week")

    multi_df = high_low_multivariable(
        high_metric=high_metric,
        low_metric=low_metric,
        high_threshold=high_threshold,
        low_threshold=low_threshold,
        week_lag=multi_week,
        limit=20,
    )
    st.dataframe(multi_df, use_container_width=True, hide_index=True)

    if not multi_df.empty:
        fig = px.scatter(
            multi_df,
            x="high_metric_value",
            y="low_metric_value",
            size="orders",
            color="COUNTRY",
            hover_data=["CITY", "ZONE", "ZONE_TYPE"],
            title=f"{high_metric} alto vs {low_metric} bajo",
        )
        st.plotly_chart(fig, use_container_width=True)

with tab_data:
    st.subheader("Preview tabla SQL")
    st.dataframe(sample_rows(100), use_container_width=True, hide_index=True)
