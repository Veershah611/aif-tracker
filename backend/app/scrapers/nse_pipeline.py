"""
NSE/BSE Delta Engine Pipeline.

Fetches bulk/block/large deals from NSE and BSE APIs,
matches them against tracked fund aliases, and inserts
matched trades into the trade ledger.
"""

from datetime import date

from app.core.config import NSE_LARGE_DEAL_API, BSE_BULK_DEAL_URL
from app.core.fund_registry import ALIAS_TO_FUND_ID
from app.db.operations import insert_trade
from app.scrapers.security_master import lookup_isin
from app.engine.fuzzy_matcher import match_fund
from app.core.http_client import NSESession, BSESession
from app.core.logger import get_logger

logger = get_logger("nse_pipeline")


def get_nse_large_deals():
    """Fetches large deals data from NSE using the project's NSESession."""
    try:
        logger.info("Fetching Large Deals data from NSE...")
        session = NSESession()
        response = session.get(NSE_LARGE_DEAL_API)
        return response.json()
    except Exception as e:
        logger.error("Error fetching NSE deals: %s", e)
        return {}


def get_bse_bulk_deals():
    """Fetches bulk deals data from BSE using the project's BSESession."""
    try:
        logger.info("Fetching Bulk Deals data from BSE...")
        session = BSESession()
        response = session.get(BSE_BULK_DEAL_URL)
        return response.json()
    except Exception as e:
        logger.error("Error fetching BSE deals: %s", e)
        return {}


def _parse_numeric(value, as_int=False):
    """Safely parse a numeric string, stripping commas."""
    if value is None:
        return 0 if as_int else 0.0
    cleaned = str(value).replace(",", "").strip()
    if not cleaned:
        return 0 if as_int else 0.0
    try:
        return int(float(cleaned)) if as_int else float(cleaned)
    except (ValueError, TypeError):
        return 0 if as_int else 0.0


def process_and_update():
    """Processes deals and inserts matched ones into the database."""
    nse_count = 0
    bse_count = 0
    today = date.today()

    # ── 1. Process NSE Large Deals ───────────────────────────────────────
    nse_data = get_nse_large_deals()
    for deal_type in ["BULK", "BLOCK", "SHORT"]:
        deals = nse_data.get(deal_type + "deals", [])
        for deal in deals:
            client_name = deal.get("clientName", "")
            fund_id = match_fund(client_name)
            if not fund_id:
                continue

            stock_name = deal.get("symbol", "")
            action = deal.get("buyOrSell", "").upper()
            qty = _parse_numeric(deal.get("quantity"), as_int=True)
            price = _parse_numeric(deal.get("tradePrice"))

            if action in ["BUY", "SELL"] and qty > 0:
                isin = lookup_isin(company_name=stock_name)
                transaction_type = "BUY" if action == "BUY" else "SELL"

                success = insert_trade(
                    fund_id=fund_id,
                    stock_name=stock_name,
                    trade_date=today,
                    transaction_type=transaction_type,
                    quantity=qty,
                    execution_price=price,
                    exchange="NSE",
                    deal_type=deal_type,
                    raw_client_name=client_name,
                    isin=isin,
                    source="nse_api",
                )
                if success:
                    nse_count += 1
                    logger.info("NSE Match: %s %s %d %s", fund_id, transaction_type, qty, stock_name)

    # ── 2. Process BSE Bulk Deals ────────────────────────────────────────
    bse_data = get_bse_bulk_deals()
    bse_deals = bse_data.get("Data", []) if isinstance(bse_data, dict) else []
    for deal in bse_deals:
        client_name = deal.get("ClientName", "")
        fund_id = match_fund(client_name)
        if not fund_id:
            continue

        stock_name = deal.get("ScripName", "")
        action = deal.get("BuySell", "").upper()
        qty = _parse_numeric(deal.get("Quantity"), as_int=True)
        price = _parse_numeric(deal.get("Price"))

        if action in ["B", "S", "BUY", "SELL"] and qty > 0:
            transaction_type = "BUY" if action in ["B", "BUY"] else "SELL"
            isin = lookup_isin(company_name=stock_name)

            success = insert_trade(
                fund_id=fund_id,
                stock_name=stock_name,
                trade_date=today,
                transaction_type=transaction_type,
                quantity=qty,
                execution_price=price,
                exchange="BSE",
                deal_type="BULK",
                raw_client_name=client_name,
                isin=isin,
                source="bse_api",
            )
            if success:
                bse_count += 1
                logger.info("BSE Match: %s %s %d %s", fund_id, transaction_type, qty, stock_name)

    return {"NSE": nse_count, "BSE": bse_count}


if __name__ == "__main__":
    process_and_update()
