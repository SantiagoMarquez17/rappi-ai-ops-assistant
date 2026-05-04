from dataclasses import dataclass

import pandas as pd

from src.database import TABLE_NAME, run_query


@dataclass
class InsightSection:
    title: str
    description: str
    data: pd.DataFrame
    recommendation: str


def detect_anomalies(limit: int = 10) -> InsightSection:
    sql = f"""
        WITH current_vs_previous AS (
            SELECT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_KEY,
                ZONE_TYPE,
                METRIC,
                MAX(CASE WHEN WEEK_LAG = 1 THEN METRIC_VALUE END) AS previous_value,
                MAX(CASE WHEN WEEK_LAG = 0 THEN METRIC_VALUE END) AS current_value,
                MAX(CASE WHEN WEEK_LAG = 0 THEN ORDERS_VALUE END) AS orders
            FROM {TABLE_NAME}
            WHERE WEEK_LAG IN (0, 1)
            GROUP BY COUNTRY, CITY, ZONE, ZONE_KEY, ZONE_TYPE, METRIC
        )
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_TYPE,
            METRIC,
            previous_value,
            current_value,
            ROUND(current_value - previous_value, 4) AS absolute_change,
            ROUND((current_value - previous_value) / NULLIF(ABS(previous_value), 0), 4) AS pct_change,
            orders
        FROM current_vs_previous
        WHERE previous_value IS NOT NULL
          AND current_value IS NOT NULL
          AND ABS((current_value - previous_value) / NULLIF(ABS(previous_value), 0)) >= 0.10
        ORDER BY ABS(pct_change) DESC NULLS LAST, orders DESC NULLS LAST
        LIMIT {limit}
    """
    data = run_query(sql)
    return InsightSection(
        title="Anomalias semana contra semana",
        description="Cambios mayores al 10% entre L1W y L0W.",
        data=data,
        recommendation="Priorizar anomalías con alto volumen de órdenes y validar si son cambios operativos reales o ruido de datos.",
    )


def detect_declining_trends(limit: int = 10) -> InsightSection:
    sql = f"""
        WITH ordered AS (
            SELECT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_KEY,
                ZONE_TYPE,
                METRIC,
                MAX(CASE WHEN WEEK_LAG = 3 THEN METRIC_VALUE END) AS value_l3w,
                MAX(CASE WHEN WEEK_LAG = 2 THEN METRIC_VALUE END) AS value_l2w,
                MAX(CASE WHEN WEEK_LAG = 1 THEN METRIC_VALUE END) AS value_l1w,
                MAX(CASE WHEN WEEK_LAG = 0 THEN METRIC_VALUE END) AS value_l0w,
                MAX(CASE WHEN WEEK_LAG = 0 THEN ORDERS_VALUE END) AS orders
            FROM {TABLE_NAME}
            WHERE WEEK_LAG BETWEEN 0 AND 3
            GROUP BY COUNTRY, CITY, ZONE, ZONE_KEY, ZONE_TYPE, METRIC
        )
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_TYPE,
            METRIC,
            value_l3w,
            value_l2w,
            value_l1w,
            value_l0w,
            ROUND(value_l0w - value_l3w, 4) AS total_drop,
            orders
        FROM ordered
        WHERE value_l3w > value_l2w
          AND value_l2w > value_l1w
          AND value_l1w > value_l0w
        ORDER BY ABS(total_drop) DESC, orders DESC NULLS LAST
        LIMIT {limit}
    """
    data = run_query(sql)
    return InsightSection(
        title="Tendencias preocupantes",
        description="Metricas con deterioro consistente durante 3 semanas consecutivas.",
        data=data,
        recommendation="Abrir revisión operacional por zona y métrica; si coincide con alto volumen, escalar como prioridad semanal.",
    )


def detect_benchmark_gaps(limit: int = 10) -> InsightSection:
    sql = f"""
        WITH current_week AS (
            SELECT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_TYPE,
                ZONE_PRIORITIZATION,
                METRIC,
                METRIC_VALUE,
                ORDERS_VALUE
            FROM {TABLE_NAME}
            WHERE WEEK_LAG = 0
        ),
        benchmarked AS (
            SELECT
                *,
                AVG(METRIC_VALUE) OVER (
                    PARTITION BY COUNTRY, ZONE_TYPE, METRIC
                ) AS peer_avg
            FROM current_week
        )
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_TYPE,
            METRIC,
            METRIC_VALUE,
            ROUND(peer_avg, 4) AS peer_avg,
            ROUND(METRIC_VALUE - peer_avg, 4) AS gap_vs_peers,
            ORDERS_VALUE AS orders
        FROM benchmarked
        WHERE peer_avg IS NOT NULL
          AND METRIC_VALUE < peer_avg * 0.85
        ORDER BY ABS(gap_vs_peers) DESC, orders DESC NULLS LAST
        LIMIT {limit}
    """
    data = run_query(sql)
    return InsightSection(
        title="Benchmarking contra zonas similares",
        description="Zonas por debajo del 85% del promedio de pares del mismo pais y tipo de zona.",
        data=data,
        recommendation="Comparar prácticas operativas de zonas pares con mejor desempeño y replicar acciones en zonas rezagadas.",
    )


def detect_correlations(limit: int = 10) -> InsightSection:
    sql = f"""
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_KEY,
            WEEK_LAG,
            METRIC,
            METRIC_VALUE
        FROM {TABLE_NAME}
        WHERE WEEK_LAG = 0
    """
    long_df = run_query(sql)

    if long_df.empty:
        data = pd.DataFrame()
    else:
        wide_df = long_df.pivot_table(
            index=["COUNTRY", "CITY", "ZONE", "ZONE_KEY", "WEEK_LAG"],
            columns="METRIC",
            values="METRIC_VALUE",
            aggfunc="mean",
        )
        corr_matrix = wide_df.corr(numeric_only=True)
        corr_matrix.index.name = "metric_a"
        corr_matrix.columns.name = "metric_b"
        corr = corr_matrix.stack().reset_index()
        corr.columns = ["metric_a", "metric_b", "correlation"]
        corr = corr[corr["metric_a"] < corr["metric_b"]]
        corr["abs_correlation"] = corr["correlation"].abs()
        data = corr.sort_values("abs_correlation", ascending=False).head(limit)

    return InsightSection(
        title="Correlaciones entre metricas",
        description="Relaciones lineales fuertes entre metricas en la semana actual.",
        data=data,
        recommendation="Usar correlaciones como hipótesis, no como causalidad; validar con contexto operativo antes de tomar decisiones.",
    )


def detect_opportunities(limit: int = 10) -> InsightSection:
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
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_TYPE,
            lead_penetration,
            perfect_orders,
            orders
        FROM pivoted
        WHERE orders IS NOT NULL
          AND lead_penetration IS NOT NULL
          AND perfect_orders IS NOT NULL
          AND orders >= 1000
          AND (lead_penetration < 0.50 OR perfect_orders < 0.85)
        ORDER BY orders DESC
        LIMIT {limit}
    """
    data = run_query(sql)
    return InsightSection(
        title="Oportunidades de alto volumen",
        description="Zonas con volumen relevante y señales de mejora en penetración o calidad.",
        data=data,
        recommendation="Priorizar intervenciones en zonas de alto volumen donde pequeñas mejoras de métrica pueden mover más órdenes.",
    )


def generate_insights() -> list[InsightSection]:
    return [
        detect_anomalies(),
        detect_declining_trends(),
        detect_benchmark_gaps(),
        detect_correlations(),
        detect_opportunities(),
    ]


def generate_markdown_report(sections: list[InsightSection]) -> str:
    lines = [
        "# Reporte Ejecutivo - Rappi AI Ops Assistant",
        "",
        "## Resumen ejecutivo",
        "",
    ]

    top_findings = []
    for section in sections:
        if not section.data.empty:
            top_findings.append(f"- **{section.title}:** {section.description}")

    lines.extend(top_findings[:5] or ["- No se encontraron hallazgos críticos con las reglas actuales."])
    lines.append("")

    for section in sections:
        lines.append(f"## {section.title}")
        lines.append("")
        lines.append(section.description)
        lines.append("")
        lines.append(f"**Recomendacion:** {section.recommendation}")
        lines.append("")

        if section.data.empty:
            lines.append("No se encontraron casos para esta categoría.")
        else:
            lines.append(section.data.head(10).to_markdown(index=False))
        lines.append("")

    return "\n".join(lines)
