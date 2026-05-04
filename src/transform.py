import pandas as pd

from src.text_utils import clean_text, country_name_from_code, normalize_code


INPUT_ID_COLUMNS = [
    "COUNTRY",
    "CITY",
    "ZONE",
    "ZONE_TYPE",
    "ZONE_PRIORITIZATION",
    "METRIC",
]

ORDER_ID_COLUMNS = [
    "COUNTRY",
    "CITY",
    "ZONE",
    "METRIC",
]


def normalize_week_label(week_column: str) -> int:
    """Convert source week columns like L8W_ROLL or L8W into numeric lag values."""
    return int(week_column.split("W")[0].replace("L", ""))


def build_zone_key(df: pd.DataFrame) -> pd.Series:
    """Build a readable key for zone-level joins and debugging."""
    return df["COUNTRY_CODE"] + "|" + df["CITY"] + "|" + df["ZONE"]


def clean_input_metrics(input_metrics: pd.DataFrame) -> pd.DataFrame:
    """Clean text fields before transforming and joining."""
    clean_df = input_metrics.copy()

    clean_df["COUNTRY_CODE"] = clean_df["COUNTRY"].apply(normalize_code)
    clean_df["COUNTRY"] = clean_df["COUNTRY_CODE"].apply(country_name_from_code)

    for column in ["CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC"]:
        clean_df[column] = clean_df[column].apply(clean_text)

    clean_df["ZONE_KEY"] = build_zone_key(clean_df)

    return clean_df


def clean_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Clean order fields using the same rules as the metrics dataset."""
    clean_df = orders.copy()

    clean_df["COUNTRY_CODE"] = clean_df["COUNTRY"].apply(normalize_code)
    clean_df["COUNTRY"] = clean_df["COUNTRY_CODE"].apply(country_name_from_code)

    for column in ["CITY", "ZONE", "METRIC"]:
        clean_df[column] = clean_df[column].apply(clean_text)

    clean_df["ZONE_KEY"] = build_zone_key(clean_df)

    return clean_df


def transform_input_metrics(input_metrics: pd.DataFrame) -> pd.DataFrame:
    """Convert cleaned input metrics from wide weekly columns to long format."""
    week_columns = [col for col in input_metrics.columns if col.startswith("L") and col.endswith("W_ROLL")]

    long_df = input_metrics.melt(
        id_vars=[
            "COUNTRY_CODE",
            "COUNTRY",
            "CITY",
            "ZONE",
            "ZONE_KEY",
            "ZONE_TYPE",
            "ZONE_PRIORITIZATION",
            "METRIC",
        ],
        value_vars=week_columns,
        var_name="WEEK_LABEL",
        value_name="METRIC_VALUE",
    )

    long_df["WEEK_LAG"] = long_df["WEEK_LABEL"].apply(normalize_week_label)
    long_df["METRIC_VALUE"] = pd.to_numeric(long_df["METRIC_VALUE"], errors="coerce").astype("float64")

    group_columns = [
        "COUNTRY_CODE",
        "COUNTRY",
        "CITY",
        "ZONE",
        "ZONE_KEY",
        "ZONE_TYPE",
        "ZONE_PRIORITIZATION",
        "METRIC",
        "WEEK_LABEL",
        "WEEK_LAG",
    ]

    return (
        long_df.groupby(group_columns, as_index=False, dropna=False)
        .agg(METRIC_VALUE=("METRIC_VALUE", "mean"))
    )


def transform_orders(orders: pd.DataFrame) -> pd.DataFrame:
    """Convert cleaned order data from wide weekly columns to long format."""
    week_columns = [col for col in orders.columns if col.startswith("L") and col.endswith("W")]

    long_df = orders.melt(
        id_vars=["COUNTRY_CODE", "COUNTRY", "CITY", "ZONE", "ZONE_KEY"],
        value_vars=week_columns,
        var_name="WEEK_LABEL",
        value_name="ORDERS_VALUE",
    )

    long_df["WEEK_LAG"] = long_df["WEEK_LABEL"].apply(normalize_week_label)
    long_df["ORDERS_VALUE"] = pd.to_numeric(long_df["ORDERS_VALUE"], errors="coerce").astype("float64")

    return long_df[
        [
            "COUNTRY_CODE",
            "COUNTRY",
            "CITY",
            "ZONE",
            "ZONE_KEY",
            "WEEK_LAG",
            "ORDERS_VALUE",
        ]
    ]


def build_analytical_dataset(input_metrics: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Build an extended dataset using metrics as the master table."""
    clean_metrics = clean_input_metrics(input_metrics)
    clean_order_data = clean_orders(orders)

    metrics_long = transform_input_metrics(clean_metrics)
    orders_long = transform_orders(clean_order_data)

    analytical_df = metrics_long.merge(
        orders_long,
        on=["COUNTRY_CODE", "COUNTRY", "CITY", "ZONE", "ZONE_KEY", "WEEK_LAG"],
        how="left",
        validate="many_to_one",
    )

    analytical_df["HAS_ORDERS_MATCH"] = analytical_df["ORDERS_VALUE"].notna()

    return analytical_df[
        [
            "COUNTRY_CODE",
            "COUNTRY",
            "CITY",
            "ZONE",
            "ZONE_KEY",
            "ZONE_TYPE",
            "ZONE_PRIORITIZATION",
            "METRIC",
            "WEEK_LABEL",
            "WEEK_LAG",
            "METRIC_VALUE",
            "ORDERS_VALUE",
            "HAS_ORDERS_MATCH",
        ]
    ].sort_values(
        ["COUNTRY", "CITY", "ZONE", "METRIC", "WEEK_LAG"],
        ascending=[True, True, True, True, False],
    ).reset_index(drop=True)
