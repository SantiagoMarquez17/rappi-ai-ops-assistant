import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.database import TABLE_NAME, run_query  # noqa: E402


QUERIES = {
    "Top 5 zonas por Lead Penetration semana actual": f"""
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_TYPE,
            METRIC_VALUE AS lead_penetration,
            ORDERS_VALUE AS orders
        FROM {TABLE_NAME}
        WHERE METRIC = 'Lead Penetration'
          AND WEEK_LAG = 0
        ORDER BY METRIC_VALUE DESC
        LIMIT 5
    """,
    "Perfect Orders Wealthy vs Non Wealthy en Mexico": f"""
        SELECT
            ZONE_TYPE,
            ROUND(AVG(METRIC_VALUE), 4) AS avg_perfect_orders,
            COUNT(DISTINCT ZONE_KEY) AS zones
        FROM {TABLE_NAME}
        WHERE COUNTRY = 'Mexico'
          AND METRIC = 'Perfect Orders'
          AND WEEK_LAG = 0
        GROUP BY ZONE_TYPE
        ORDER BY avg_perfect_orders DESC
    """,
    "Tendencia Gross Profit UE Chapinero ultimas 8 semanas": f"""
        SELECT
            WEEK_LAG,
            METRIC_VALUE AS gross_profit_ue,
            ORDERS_VALUE AS orders
        FROM {TABLE_NAME}
        WHERE METRIC = 'Gross Profit UE'
          AND ZONE = 'Chapinero'
          AND WEEK_LAG BETWEEN 0 AND 7
        ORDER BY WEEK_LAG DESC
    """,
    "Alto Lead Penetration y bajo Perfect Orders": f"""
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
        WHERE lead_penetration >= 0.7
          AND perfect_orders <= 0.8
        ORDER BY orders DESC NULLS LAST
        LIMIT 10
    """,
}


def main() -> None:
    for title, sql in QUERIES.items():
        print()
        print("=" * 90)
        print(title)
        print("=" * 90)
        result = run_query(sql)
        print(result.to_string(index=False))


if __name__ == "__main__":
    main()

