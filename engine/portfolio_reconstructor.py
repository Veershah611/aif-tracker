"""
Portfolio Reconstructor.

Implements the core algorithm from document §5:
  Current_Holdings(ISIN) = Baseline_Quantity(ISIN)
                          + Σ(Buy_Quantities after baseline_date)
                          - Σ(Sell_Quantities after baseline_date)

Synthesizes baseline snapshots with trade ledger deltas to produce
the fund's estimated current portfolio.
"""

from typing import Optional
import pandas as pd

from config.fund_registry import FUND_BY_ID, ALL_FUNDS
from database.operations import get_latest_baseline, get_trades_since
from utils.logger import get_logger

logger = get_logger(__name__)


def reconstruct_portfolio(fund_id: str) -> pd.DataFrame:
    """
    Reconstruct the current portfolio for a given fund.

    Algorithm:
    1. Load the most recent baseline snapshot
    2. Load all trades since that baseline date
    3. For each ISIN/stock: current_qty = baseline_qty + buys - sells

    Returns a DataFrame with columns:
        stock_name, isin, baseline_qty, total_buys, total_sells,
        net_delta, current_qty, baseline_date
    """
    fund = FUND_BY_ID.get(fund_id)
    if not fund:
        logger.error("Unknown fund_id: %s", fund_id)
        return pd.DataFrame()

    # Step 1: Get latest baseline
    baseline_df = get_latest_baseline(fund_id)
    if baseline_df.empty:
        logger.warning("No baseline data for %s. Returning empty portfolio.", fund.fund_name)
        return pd.DataFrame()

    baseline_date = baseline_df["report_date"].iloc[0]
    logger.info(
        "Reconstructing portfolio for %s (baseline: %s, %d holdings)",
        fund.fund_name, baseline_date, len(baseline_df)
    )

    # Step 2: Get all trades since baseline
    trades_df = get_trades_since(fund_id, baseline_date)

    if trades_df.empty:
        # No deltas — baseline IS the current portfolio
        logger.info("No trades since baseline. Current portfolio = baseline.")
        result = baseline_df.copy()
        result["total_buys"] = 0
        result["total_sells"] = 0
        result["net_delta"] = 0
        result["current_qty"] = result["quantity_held"]
        result["baseline_date"] = baseline_date
        result.rename(columns={"quantity_held": "baseline_qty"}, inplace=True)
        return result[
            ["stock_name", "isin", "baseline_qty", "total_buys",
             "total_sells", "net_delta", "current_qty",
             "holding_percent", "holding_value", "baseline_date"]
        ]

    # Step 3: Aggregate trade deltas per stock
    # Use ISIN as primary key; fall back to stock_name if ISIN is missing
    trades_df["merge_key"] = trades_df["isin"].fillna(trades_df["stock_name"])

    buys = trades_df[trades_df["transaction_type"] == "BUY"].groupby("merge_key")["quantity"].sum()
    sells = trades_df[trades_df["transaction_type"] == "SELL"].groupby("merge_key")["quantity"].sum()

    delta_df = pd.DataFrame({
        "total_buys": buys,
        "total_sells": sells,
    }).fillna(0).astype(int)
    delta_df["net_delta"] = delta_df["total_buys"] - delta_df["total_sells"]

    # Step 4: Merge baseline with deltas
    baseline_df["merge_key"] = baseline_df["isin"].fillna(baseline_df["stock_name"])
    baseline_df.rename(columns={"quantity_held": "baseline_qty"}, inplace=True)

    result = baseline_df.merge(delta_df, on="merge_key", how="outer")

    # Fill NaN for stocks only in trades (new positions not in baseline)
    result["baseline_qty"] = result["baseline_qty"].fillna(0).astype(int)
    result["total_buys"] = result["total_buys"].fillna(0).astype(int)
    result["total_sells"] = result["total_sells"].fillna(0).astype(int)
    result["net_delta"] = result["net_delta"].fillna(0).astype(int)

    # Calculate current quantity
    result["current_qty"] = result["baseline_qty"] + result["net_delta"]
    result["baseline_date"] = baseline_date

    # For new positions (only in trades), try to fill stock_name from trades
    if "stock_name" not in result.columns or result["stock_name"].isna().any():
        trade_names = trades_df.drop_duplicates("merge_key").set_index("merge_key")["stock_name"]
        mask = result["stock_name"].isna()
        result.loc[mask, "stock_name"] = result.loc[mask, "merge_key"].map(trade_names)

    # Remove fully exited positions (current_qty <= 0) — but keep for reporting
    result["status"] = "HELD"
    result.loc[result["current_qty"] <= 0, "status"] = "EXITED"

    # Sort by current quantity descending
    result = result.sort_values("current_qty", ascending=False)

    columns = [
        "stock_name", "isin", "baseline_qty", "total_buys",
        "total_sells", "net_delta", "current_qty", "status",
        "holding_percent", "holding_value", "baseline_date",
    ]
    # Only include columns that exist
    columns = [c for c in columns if c in result.columns]

    logger.info(
        "Reconstruction complete: %d held, %d exited",
        (result["status"] == "HELD").sum(),
        (result["status"] == "EXITED").sum(),
    )

    return result[columns].reset_index(drop=True)


def reconstruct_all_portfolios() -> dict:
    """
    Reconstruct portfolios for all 8 target funds.
    Returns dict of {fund_id: DataFrame}.
    """
    portfolios = {}
    for fund in ALL_FUNDS:
        logger.info("=" * 60)
        df = reconstruct_portfolio(fund.fund_id)
        portfolios[fund.fund_id] = df
    return portfolios


def display_portfolio(fund_id: str):
    """Pretty-print a fund's reconstructed portfolio to console."""
    fund = FUND_BY_ID.get(fund_id)
    df = reconstruct_portfolio(fund_id)

    if df.empty:
        print(f"\n  No data available for {fund.fund_name if fund else fund_id}\n")
        return

    fund_name = fund.fund_name if fund else fund_id
    baseline_date = df["baseline_date"].iloc[0] if "baseline_date" in df.columns else "N/A"

    print(f"\n{'=' * 80}")
    print(f"  {fund_name}")
    print(f"  Baseline Date: {baseline_date}")
    print(f"  Total Holdings: {len(df[df.get('status', 'HELD') == 'HELD'])} active")
    print(f"{'=' * 80}")

    # Display columns
    display_cols = ["stock_name", "current_qty", "baseline_qty", "net_delta", "status"]
    display_cols = [c for c in display_cols if c in df.columns]

    pd.set_option("display.max_rows", None)
    pd.set_option("display.max_colwidth", 35)
    pd.set_option("display.width", 120)
    print(df[display_cols].to_string(index=False))
    print()
