import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import DUCKDB_PATH  # noqa: E402
from src.database import TABLE_NAME, build_database, run_query  # noqa: E402


def main() -> None:
    print(f"Building DuckDB database at: {DUCKDB_PATH}")
    build_database()

    summary = run_query(
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

    print(summary.to_string(index=False))
    print(f"Table created: {TABLE_NAME}")


if __name__ == "__main__":
    main()

