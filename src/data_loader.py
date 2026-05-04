import pandas as pd

from src.config import RAW_EXCEL_PATH


INPUT_METRICS_SHEET = "RAW_INPUT_METRICS"
ORDERS_SHEET = "RAW_ORDERS"


def load_raw_input_metrics(path=RAW_EXCEL_PATH) -> pd.DataFrame:
    """Load operational input metrics from the source Excel file."""
    return pd.read_excel(path, sheet_name=INPUT_METRICS_SHEET)


def load_raw_orders(path=RAW_EXCEL_PATH) -> pd.DataFrame:
    """Load orders by zone from the source Excel file."""
    return pd.read_excel(path, sheet_name=ORDERS_SHEET)


def load_all_raw_data(path=RAW_EXCEL_PATH) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load both required raw datasets."""
    input_metrics = load_raw_input_metrics(path)
    orders = load_raw_orders(path)
    return input_metrics, orders

