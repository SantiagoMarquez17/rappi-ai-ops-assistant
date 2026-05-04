import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT))

from src.config import METRICS_WITH_ORDERS_PATH, RAW_EXCEL_PATH  # noqa: E402
from src.data_loader import load_all_raw_data  # noqa: E402
from src.transform import build_analytical_dataset  # noqa: E402


def main() -> None:
    print(f"Reading raw data from: {RAW_EXCEL_PATH}")
    input_metrics, orders = load_all_raw_data()

    print(f"Input metrics rows: {len(input_metrics):,}")
    print(f"Orders rows: {len(orders):,}")

    analytical_df = build_analytical_dataset(input_metrics, orders)

    METRICS_WITH_ORDERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    analytical_df.to_csv(METRICS_WITH_ORDERS_PATH, index=False)

    print(f"Metrics long rows: {len(analytical_df):,}")
    print(f"Countries: {analytical_df['COUNTRY'].nunique():,}")
    print(f"Cities: {analytical_df['CITY'].nunique():,}")
    print(f"Zones: {analytical_df[['COUNTRY', 'CITY', 'ZONE']].drop_duplicates().shape[0]:,}")
    print(f"Metrics: {analytical_df['METRIC'].nunique():,}")
    print(f"Order match rate: {analytical_df['HAS_ORDERS_MATCH'].mean():.2%}")
    print(f"Saved extended dataset to: {METRICS_WITH_ORDERS_PATH}")


if __name__ == "__main__":
    main()
