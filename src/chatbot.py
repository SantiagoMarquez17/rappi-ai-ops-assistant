from dataclasses import dataclass

import pandas as pd

from src.database import TABLE_NAME, run_query
from src.llm import interpret_question, summarize_answer
from src.text_utils import clean_text


DEFAULT_METRICS = [
    "Lead Penetration",
    "Perfect Orders",
    "Gross Profit UE",
    "Orders",
]


@dataclass
class BotResponse:
    answer: str
    sql: str
    data: pd.DataFrame
    chart_type: str | None = None
    followups: list[str] | None = None


def get_available_values() -> dict[str, list[str]]:
    metrics = run_query(f"SELECT DISTINCT METRIC FROM {TABLE_NAME} ORDER BY METRIC")["METRIC"].tolist()
    countries = run_query(f"SELECT DISTINCT COUNTRY FROM {TABLE_NAME} ORDER BY COUNTRY")["COUNTRY"].tolist()
    cities = run_query(f"SELECT DISTINCT CITY FROM {TABLE_NAME} ORDER BY CITY")["CITY"].tolist()
    zones = run_query(f"SELECT DISTINCT ZONE FROM {TABLE_NAME} ORDER BY ZONE")["ZONE"].tolist()

    return {
        "metrics": metrics,
        "countries": countries,
        "cities": cities,
        "zones": zones,
    }


def find_value(question_clean: str, values: list[str]) -> str | None:
    for value in values:
        if clean_text(value).upper() in question_clean:
            return value
    return None


def normalize_plan_value(value: object, allowed_values: list[str]) -> str | None:
    """Map an LLM-provided value to an allowed dataset value using cleaned text."""
    if value is None:
        return None

    value_clean = clean_text(value).upper()
    for allowed_value in allowed_values:
        if clean_text(allowed_value).upper() == value_clean:
            return allowed_value

    for allowed_value in allowed_values:
        allowed_clean = clean_text(allowed_value).upper()
        if value_clean in allowed_clean or allowed_clean in value_clean:
            return allowed_value

    return None


def detect_metric(question_clean: str, metrics: list[str]) -> str | None:
    metric = find_value(question_clean, metrics)
    if metric:
        return metric

    synonyms = {
        "ORDENES": "Orders",
        "ORDERS": "Orders",
        "GANANCIA": "Gross Profit UE",
        "GROSS PROFIT": "Gross Profit UE",
        "PERFECT ORDER": "Perfect Orders",
        "PERFECT ORDERS": "Perfect Orders",
        "LEAD": "Lead Penetration",
        "PENETRATION": "Lead Penetration",
    }

    for token, metric_name in synonyms.items():
        if token in question_clean:
            return metric_name

    return None


def detect_country(question_clean: str, countries: list[str]) -> str | None:
    country = find_value(question_clean, countries)
    if country:
        return country

    country_synonyms = {
        "MEXICO": "Mexico",
        "COLOMBIA": "Colombia",
        "BRASIL": "Brasil",
        "BRAZIL": "Brasil",
        "ECUADOR": "Ecuador",
        "ARGENTINA": "Argentina",
        "CHILE": "Chile",
        "PERU": "Peru",
        "URUGUAY": "Uruguay",
        "COSTA RICA": "Costa Rica",
    }

    for token, country_name in country_synonyms.items():
        if token in question_clean:
            return country_name

    return None


def trend_query(metric: str, zone: str, country: str | None = None, city: str | None = None) -> BotResponse:
    filters = [
        f"METRIC = '{metric}'",
        f"ZONE = '{zone}'",
        "WEEK_LAG BETWEEN 0 AND 8",
    ]
    if country:
        filters.append(f"COUNTRY = '{country}'")
    if city:
        filters.append(f"CITY = '{city}'")

    sql = f"""
        SELECT
            WEEK_LAG,
            AVG(METRIC_VALUE) AS metric_value,
            MAX(ORDERS_VALUE) AS orders
        FROM {TABLE_NAME}
        WHERE {' AND '.join(filters)}
        GROUP BY WEEK_LAG
        ORDER BY WEEK_LAG DESC
    """
    data = run_query(sql)
    return BotResponse(
        answer=f"Evolucion de {metric} en {zone}. Uso promedio si la zona aparece en mas de una ciudad/pais.",
        sql=sql,
        data=data,
        chart_type="line",
        followups=[
            "Comparar esta tendencia contra zonas similares",
            "Revisar si las ordenes crecieron o cayeron en el mismo periodo",
        ],
    )


def top_zones_query(metric: str, country: str | None = None, limit: int = 5) -> BotResponse:
    country_filter = f"AND COUNTRY = '{country}'" if country else ""
    sql = f"""
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_TYPE,
            ZONE_PRIORITIZATION,
            METRIC_VALUE AS metric_value,
            ORDERS_VALUE AS orders
        FROM {TABLE_NAME}
        WHERE METRIC = '{metric}'
          AND WEEK_LAG = 0
          {country_filter}
        ORDER BY METRIC_VALUE DESC NULLS LAST
        LIMIT {limit}
    """
    data = run_query(sql)
    scope = f" en {country}" if country else ""
    return BotResponse(
        answer=f"Estas son las top {limit} zonas por {metric}{scope} en la semana actual.",
        sql=sql,
        data=data,
        chart_type="bar",
        followups=[
            f"Ver tendencia de {metric} para la primera zona",
            "Cruzar este ranking contra Perfect Orders",
        ],
    )


def compare_zone_type_query(metric: str, country: str) -> BotResponse:
    sql = f"""
        SELECT
            ZONE_TYPE,
            ROUND(AVG(METRIC_VALUE), 4) AS avg_metric_value,
            COUNT(DISTINCT ZONE_KEY) AS zones,
            ROUND(AVG(ORDERS_VALUE), 2) AS avg_orders
        FROM {TABLE_NAME}
        WHERE COUNTRY = '{country}'
          AND METRIC = '{metric}'
          AND WEEK_LAG = 0
        GROUP BY ZONE_TYPE
        ORDER BY avg_metric_value DESC
    """
    data = run_query(sql)
    return BotResponse(
        answer=f"Comparacion de {metric} entre tipos de zona en {country}.",
        sql=sql,
        data=data,
        chart_type="bar",
        followups=[
            "Identificar zonas Wealthy con peor desempeno",
            "Comparar contra volumen de ordenes",
        ],
    )


def high_low_query() -> BotResponse:
    sql = f"""
        WITH current_week AS (
            SELECT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_KEY,
                ZONE_TYPE,
                METRIC,
                METRIC_VALUE,
                ORDERS_VALUE
            FROM {TABLE_NAME}
            WHERE WEEK_LAG = 0
              AND METRIC IN ('Lead Penetration', 'Perfect Orders')
        ),
        pivoted AS (
            SELECT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_KEY,
                ZONE_TYPE,
                MAX(CASE WHEN METRIC = 'Lead Penetration' THEN METRIC_VALUE END) AS lead_penetration,
                MAX(CASE WHEN METRIC = 'Perfect Orders' THEN METRIC_VALUE END) AS perfect_orders,
                MAX(ORDERS_VALUE) AS orders
            FROM current_week
            GROUP BY COUNTRY, CITY, ZONE, ZONE_KEY, ZONE_TYPE
        )
        SELECT *
        FROM pivoted
        WHERE lead_penetration >= 0.70
          AND perfect_orders <= 0.80
        ORDER BY orders DESC NULLS LAST
        LIMIT 10
    """
    data = run_query(sql)
    return BotResponse(
        answer="Zonas con alto Lead Penetration pero bajo Perfect Orders en la semana actual.",
        sql=sql,
        data=data,
        chart_type="scatter",
        followups=[
            "Priorizar las zonas con mas ordenes",
            "Revisar si Perfect Orders viene cayendo en las ultimas semanas",
        ],
    )


def growth_orders_query() -> BotResponse:
    sql = f"""
        WITH zone_orders AS (
            SELECT DISTINCT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_KEY,
                WEEK_LAG,
                ORDERS_VALUE
            FROM {TABLE_NAME}
            WHERE WEEK_LAG BETWEEN 0 AND 5
              AND HAS_ORDERS_MATCH
        ),
        growth AS (
            SELECT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_KEY,
                MAX(CASE WHEN WEEK_LAG = 5 THEN ORDERS_VALUE END) AS orders_l5w,
                MAX(CASE WHEN WEEK_LAG = 0 THEN ORDERS_VALUE END) AS orders_l0w
            FROM zone_orders
            GROUP BY COUNTRY, CITY, ZONE, ZONE_KEY
        )
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            orders_l5w,
            orders_l0w,
            orders_l0w - orders_l5w AS absolute_growth,
            ROUND((orders_l0w - orders_l5w) / NULLIF(orders_l5w, 0), 4) AS pct_growth
        FROM growth
        WHERE orders_l5w IS NOT NULL
          AND orders_l0w IS NOT NULL
        ORDER BY pct_growth DESC NULLS LAST
        LIMIT 10
    """
    data = run_query(sql)
    return BotResponse(
        answer="Estas son las zonas que mas crecieron en ordenes entre L5W y L0W. Posibles explicaciones deben validarse cruzando metricas de conversion, calidad y adopcion.",
        sql=sql,
        data=data,
        chart_type="bar",
        followups=[
            "Cruzar crecimiento contra Lead Penetration",
            "Cruzar crecimiento contra Perfect Orders",
        ],
    )


def answer_question(question: str) -> BotResponse:
    values = get_available_values()
    question_clean = clean_text(question).upper()
    metric = detect_metric(question_clean, values["metrics"]) or "Lead Penetration"
    country = detect_country(question_clean, values["countries"])
    zone = find_value(question_clean, values["zones"])
    city = find_value(question_clean, values["cities"])

    if "CREC" in question_clean and ("ORDEN" in question_clean or "ORDER" in question_clean):
        return growth_orders_query()

    if "ALTO" in question_clean and "BAJO" in question_clean:
        return high_low_query()

    if "COMPAR" in question_clean or "WEALTHY" in question_clean:
        return compare_zone_type_query(metric=metric, country=country or "Mexico")

    if "EVOLUC" in question_clean or "TENDENCIA" in question_clean or "ULTIMAS" in question_clean:
        return trend_query(metric=metric, zone=zone or "Chapinero", country=country, city=city)

    if "TOP" in question_clean or "MAYOR" in question_clean or "5" in question_clean:
        return top_zones_query(metric=metric, country=country, limit=5)

    return top_zones_query(metric=metric, country=country, limit=10)


def execute_plan(plan: dict, question: str) -> BotResponse:
    values = get_available_values()
    intent = plan.get("intent", "fallback")

    metric = normalize_plan_value(plan.get("metric"), values["metrics"]) or "Lead Penetration"
    country = normalize_plan_value(plan.get("country"), values["countries"])
    city = normalize_plan_value(plan.get("city"), values["cities"])
    zone = normalize_plan_value(plan.get("zone"), values["zones"])
    limit = int(plan.get("limit") or 5)
    limit = max(1, min(limit, 20))

    if intent == "order_growth":
        response = growth_orders_query()
    elif intent == "high_low":
        response = high_low_query()
    elif intent == "compare_zone_type":
        response = compare_zone_type_query(metric=metric, country=country or "Mexico")
    elif intent == "trend":
        response = trend_query(metric=metric, zone=zone or "Chapinero", country=country, city=city)
    elif intent == "top_zones":
        response = top_zones_query(metric=metric, country=country, limit=limit)
    else:
        response = answer_question(question)

    if not response.data.empty:
        data_markdown = response.data.head(10).to_markdown(index=False)
        response.answer = summarize_answer(question, data_markdown, response.answer)

    return response


def answer_question_with_llm(question: str) -> BotResponse:
    """Answer using LLM interpretation, falling back to deterministic rules if needed."""
    try:
        plan = interpret_question(question)
        return execute_plan(plan, question)
    except Exception as exc:
        response = answer_question(question)
        response.answer = f"{response.answer}\n\nNota: use el motor deterministico porque el LLM no estuvo disponible ({exc})."
        return response
