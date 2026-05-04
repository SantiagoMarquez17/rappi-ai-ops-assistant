import duckdb

from src.config import DUCKDB_PATH, METRICS_WITH_ORDERS_PATH


TABLE_NAME = "metrics_with_orders"


def get_connection(database_path=DUCKDB_PATH) -> duckdb.DuckDBPyConnection:
    """Open a DuckDB connection for the local analytical database."""
    return duckdb.connect(str(database_path))


def build_database() -> None:
    """Create the local DuckDB database from the transformed CSV."""
    if not METRICS_WITH_ORDERS_PATH.exists():
        raise FileNotFoundError(
            f"Missing transformed dataset: {METRICS_WITH_ORDERS_PATH}. "
            "Run scripts/build_dataset.py first."
        )

    with get_connection() as con:
        con.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
        con.execute(
            f"""
            CREATE TABLE {TABLE_NAME} AS
            SELECT *
            FROM read_csv_auto(
                ?,
                header = true,
                sample_size = -1
            )
            """,
            [str(METRICS_WITH_ORDERS_PATH)],
        )


def run_query(sql: str):
    """Run a SQL query against the local analytical database."""
    with get_connection() as con:
        return con.execute(sql).fetchdf()

