"""
Market Data Fetcher — Current Price & Market Cap from NSE.

Queries the NSE quote-equity API to get live/closing prices and
market capitalisation for stocks in the portfolio.
Uses the project's NSESession for cookie-based authentication and retry logic.
"""

from typing import Optional, Dict
import pandas as pd

from app.db.operations import resolve_isin
from app.db.connection import get_session
from app.db.models import SecurityMaster
from app.core.http_client import NSESession
from app.core.logger import get_logger

logger = get_logger(__name__)

# Module-level session (reused across calls within a single pipeline run)
_nse_session: Optional[NSESession] = None


def _get_nse_session() -> NSESession:
    """Get or create a module-level NSE session."""
    global _nse_session
    if _nse_session is None:
        _nse_session = NSESession()
    return _nse_session


def fetch_stock_quote(symbol: str) -> Dict:
    """
    Fetch current market data for a single stock from NSE.

    Args:
        symbol: NSE trading symbol (e.g., "RELIANCE", "TCS").

    Returns:
        Dict with keys:
            - current_price: Last traded price (float or None)
            - market_cap: Market capitalisation in INR (float or None)
    """
    if not symbol:
        return {"current_price": None, "market_cap": None}

    session = _get_nse_session()
    url = f"https://www.nseindia.com/api/quote-equity?symbol={symbol}"

    try:
        response = session.get(url)
        data = response.json()

        price_info = data.get("priceInfo", {})
        current_price = price_info.get("lastPrice")

        # Market cap is sometimes under "securityInfo" or derived from
        # "marketDeptOrderBook" → "tradeInfo" → "totalMarketCap"
        metadata = data.get("metadata", {})
        security_info = data.get("securityInfo", {})

        # NSE provides total market cap under different keys depending on the endpoint
        market_cap = None

        # Try trade info first
        trade_info = data.get("marketDeptOrderBook", {}).get("tradeInfo", {})
        if trade_info and trade_info.get("totalMarketCap"):
            try:
                market_cap = float(trade_info["totalMarketCap"])
            except (ValueError, TypeError):
                pass

        # If not found, try calculating from issued capital and price
        if market_cap is None and current_price:
            issued_cap = security_info.get("issuedCap") or security_info.get("issuedSize")
            if issued_cap:
                try:
                    market_cap = float(current_price) * float(issued_cap)
                except (ValueError, TypeError):
                    pass

        return {
            "current_price": float(current_price) if current_price is not None else None,
            "market_cap": market_cap,
        }

    except Exception as e:
        logger.debug("Could not fetch quote for %s: %s", symbol, e)
        return {"current_price": None, "market_cap": None}


def _resolve_symbol_from_isin(isin: str) -> Optional[str]:
    """Look up the NSE symbol for a given ISIN from the security master."""
    if not isin:
        return None
    with get_session() as session:
        sec = session.query(SecurityMaster.symbol_nse).filter_by(isin=isin).first()
        return sec[0] if sec and sec[0] else None


def _resolve_symbol_from_name(stock_name: str) -> Optional[str]:
    """Look up the NSE symbol for a stock by company name from the security master."""
    if not stock_name:
        return None
    from sqlalchemy import func
    with get_session() as session:
        # Try exact match first
        sec = session.query(SecurityMaster.symbol_nse).filter(
            func.upper(SecurityMaster.company_name) == stock_name.upper()
        ).first()
        if sec and sec[0]:
            return sec[0]

        # Try LIKE match
        sec = session.query(SecurityMaster.symbol_nse).filter(
            SecurityMaster.company_name.ilike(f"%{stock_name}%")
        ).first()
        return sec[0] if sec and sec[0] else None


def enrich_portfolio_with_market_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enrich a portfolio DataFrame with current market price and market cap.

    Adds two columns:
        - current_price: Last traded price from NSE (INR)
        - market_cap: Total market capitalisation (INR)

    Args:
        df: Portfolio DataFrame with 'isin' and/or 'stock_name' columns.

    Returns:
        The same DataFrame with two new columns appended.
    """
    if df.empty:
        df["current_price"] = pd.Series(dtype="float64")
        df["market_cap"] = pd.Series(dtype="float64")
        return df

    prices = []
    caps = []

    # Cache: symbol → quote (avoid duplicate API calls for same stock)
    quote_cache: Dict[str, Dict] = {}

    for _, row in df.iterrows():
        isin = row.get("isin")
        stock_name = row.get("stock_name", "")

        # Resolve to NSE symbol
        symbol = _resolve_symbol_from_isin(isin) if isin else None
        if not symbol:
            symbol = _resolve_symbol_from_name(stock_name)

        if symbol and symbol in quote_cache:
            quote = quote_cache[symbol]
        elif symbol:
            quote = fetch_stock_quote(symbol)
            quote_cache[symbol] = quote
            logger.debug("Fetched quote for %s: price=%s, mcap=%s",
                         symbol, quote["current_price"], quote["market_cap"])
        else:
            quote = {"current_price": None, "market_cap": None}

        prices.append(quote["current_price"])
        caps.append(quote["market_cap"])

    df["current_price"] = prices
    df["market_cap"] = caps

    fetched = sum(1 for p in prices if p is not None)
    logger.info("Market data enrichment: %d/%d stocks resolved.", fetched, len(df))

    return df
