from src.database import TABLE_NAME, run_query


def get_overview():
    return run_query(
        f"""
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT COUNTRY_CODE) AS countries,
            COUNT(DISTINCT CITY) AS cities,
            COUNT(DISTINCT ZONE_KEY) AS zones,
            COUNT(DISTINCT METRIC) AS metrics,
            ROUND(AVG(CASE WHEN HAS_ORDERS_MATCH THEN 1 ELSE 0 END) * 100, 2) AS order_match_rate_pct
        FROM {TABLE_NAME}
        """
    )


def get_filter_options():
    countries = run_query(f"SELECT DISTINCT COUNTRY FROM {TABLE_NAME} ORDER BY COUNTRY")["COUNTRY"].tolist()
    metrics = run_query(f"SELECT DISTINCT METRIC FROM {TABLE_NAME} ORDER BY METRIC")["METRIC"].tolist()
    zone_types = run_query(f"SELECT DISTINCT ZONE_TYPE FROM {TABLE_NAME} ORDER BY ZONE_TYPE")["ZONE_TYPE"].tolist()

    return {
        "countries": countries,
        "metrics": metrics,
        "zone_types": zone_types,
    }


def top_zones_by_metric(metric: str, country: str | None = None, week_lag: int = 0, limit: int = 10):
    country_filter = f"AND COUNTRY = '{country}'" if country else ""
    return run_query(
        f"""
        SELECT
            COUNTRY,
            CITY,
            ZONE,
            ZONE_TYPE,
            ZONE_PRIORITIZATION,
            METRIC_VALUE,
            ORDERS_VALUE
        FROM {TABLE_NAME}
        WHERE METRIC = '{metric}'
          AND WEEK_LAG = {week_lag}
          {country_filter}
        ORDER BY METRIC_VALUE DESC NULLS LAST
        LIMIT {limit}
        """
    )


def compare_zone_type(metric: str, country: str, week_lag: int = 0):
    return run_query(
        f"""
        SELECT
            ZONE_TYPE,
            ROUND(AVG(METRIC_VALUE), 4) AS avg_metric_value,
            COUNT(DISTINCT ZONE_KEY) AS zones,
            ROUND(AVG(ORDERS_VALUE), 2) AS avg_orders
        FROM {TABLE_NAME}
        WHERE COUNTRY = '{country}'
          AND METRIC = '{metric}'
          AND WEEK_LAG = {week_lag}
        GROUP BY ZONE_TYPE
        ORDER BY avg_metric_value DESC
        """
    )


def metric_trend(metric: str, country: str, city: str, zone: str):
    return run_query(
        f"""
        SELECT
            WEEK_LAG,
            METRIC_VALUE,
            ORDERS_VALUE
        FROM {TABLE_NAME}
        WHERE COUNTRY = '{country}'
          AND CITY = '{city}'
          AND ZONE = '{zone}'
          AND METRIC = '{metric}'
          AND WEEK_LAG BETWEEN 0 AND 8
        ORDER BY WEEK_LAG DESC
        """
    )


def high_low_multivariable(
    high_metric: str,
    low_metric: str,
    high_threshold: float,
    low_threshold: float,
    week_lag: int = 0,
    limit: int = 20,
):
    return run_query(
        f"""
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
            WHERE WEEK_LAG = {week_lag}
              AND METRIC IN ('{high_metric}', '{low_metric}')
        ),
        pivoted AS (
            SELECT
                COUNTRY,
                CITY,
                ZONE,
                ZONE_KEY,
                ZONE_TYPE,
                MAX(CASE WHEN METRIC = '{high_metric}' THEN METRIC_VALUE END) AS high_metric_value,
                MAX(CASE WHEN METRIC = '{low_metric}' THEN METRIC_VALUE END) AS low_metric_value,
                MAX(ORDERS_VALUE) AS orders
            FROM current_week
            GROUP BY COUNTRY, CITY, ZONE, ZONE_KEY, ZONE_TYPE
        )
        SELECT *
        FROM pivoted
        WHERE high_metric_value >= {high_threshold}
          AND low_metric_value <= {low_threshold}
        ORDER BY orders DESC NULLS LAST
        LIMIT {limit}
        """
    )


def sample_rows(limit: int = 100):
    return run_query(
        f"""
        SELECT *
        FROM {TABLE_NAME}
        LIMIT {limit}
        """
    )
