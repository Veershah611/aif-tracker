"""
Database CRUD operations.
All read/write helpers for the 4 core tables.
"""

from datetime import date, datetime, timezone
from typing import List, Optional
import pandas as pd
from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.db.models import (
    Entity, SecurityMaster, PortfolioBaseline, TradeLedger,
)
from app.db.connection import get_session
from app.core.logger import get_logger

logger = get_logger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# Security Master Operations
# ═══════════════════════════════════════════════════════════════════════════════

def upsert_security(
    isin: str,
    company_name: str,
    symbol_nse: str = None,
    scrip_code_bse: str = None,
    group_name: str = None,
    face_value: float = None,
    industry: str = None,
):
    """Insert or update a security in the master table."""
    with get_session() as session:
        existing = session.query(SecurityMaster).filter_by(isin=isin).first()
        if existing:
            if company_name:
                existing.company_name = company_name
            if symbol_nse:
                existing.symbol_nse = symbol_nse
            if scrip_code_bse:
                existing.scrip_code_bse = scrip_code_bse
            if group_name:
                existing.group_name = group_name
            if face_value:
                existing.face_value = face_value
            if industry:
                existing.industry = industry
            existing.last_updated = datetime.utcnow()
        else:
            session.add(SecurityMaster(
                isin=isin,
                company_name=company_name,
                symbol_nse=symbol_nse,
                scrip_code_bse=scrip_code_bse,
                group_name=group_name,
                face_value=face_value,
                industry=industry,
            ))


def bulk_upsert_securities(records: List[dict]):
    """Bulk insert/update securities. Each dict must have 'isin' and 'company_name'."""
    with get_session() as session:
        for rec in records:
            existing = session.query(SecurityMaster).filter_by(isin=rec["isin"]).first()
            if existing:
                for key, val in rec.items():
                    if val is not None and key != "isin":
                        setattr(existing, key, val)
                existing.last_updated = datetime.now(timezone.utc)
            else:
                session.add(SecurityMaster(**rec))

    logger.info("Upserted %d securities.", len(records))


def resolve_isin(symbol: str = None, scrip_code: str = None, company_name: str = None) -> Optional[str]:
    """
    Look up an ISIN from the security master by symbol, scrip code, or company name.
    Returns the ISIN string or None if not found.
    """
    with get_session() as session:
        query = session.query(SecurityMaster.isin)

        if symbol:
            result = query.filter(
                func.upper(SecurityMaster.symbol_nse) == symbol.upper()
            ).first()
            if result:
                return result[0]

        if scrip_code:
            result = query.filter(
                SecurityMaster.scrip_code_bse == str(scrip_code)
            ).first()
            if result:
                return result[0]

        if company_name:
            # Try exact match first, then LIKE
            result = query.filter(
                func.upper(SecurityMaster.company_name) == company_name.upper()
            ).first()
            if result:
                return result[0]

            result = query.filter(
                SecurityMaster.company_name.ilike(f"%{company_name}%")
            ).first()
            if result:
                return result[0]

    return None


def get_security_count() -> int:
    """Return the total number of securities in the master table."""
    with get_session() as session:
        return session.query(func.count(SecurityMaster.isin)).scalar()


# ═══════════════════════════════════════════════════════════════════════════════
# Portfolio Baseline Operations
# ═══════════════════════════════════════════════════════════════════════════════

def upsert_baseline(
    fund_id: str,
    stock_name: str,
    quantity_held: int,
    report_date: date,
    source: str,
    isin: str = None,
    holding_percent: float = None,
    holding_value: float = None,
):
    """
    Insert or update a baseline holding record.
    Deduplicates by fund_id + stock_name + report_date.
    """
    with get_session() as session:
        existing = session.query(PortfolioBaseline).filter_by(
            fund_id=fund_id,
            stock_name=stock_name,
            report_date=report_date,
        ).first()

        if existing:
            existing.quantity_held = quantity_held
            existing.isin = isin or existing.isin
            existing.holding_percent = holding_percent or existing.holding_percent
            existing.holding_value = holding_value or existing.holding_value
            existing.source = source
        else:
            session.add(PortfolioBaseline(
                fund_id=fund_id,
                isin=isin,
                stock_name=stock_name,
                quantity_held=quantity_held,
                holding_percent=holding_percent,
                holding_value=holding_value,
                report_date=report_date,
                source=source,
            ))


def bulk_upsert_baselines(records: List[dict]):
    """Bulk insert baseline records. Each dict must have fund_id, stock_name, quantity_held, report_date, source."""
    count = 0
    for rec in records:
        upsert_baseline(**rec)
        count += 1
    logger.info("Upserted %d baseline records.", count)


def get_latest_baseline(fund_id: str) -> pd.DataFrame:
    """
    Fetch the most recent baseline snapshot for a fund.
    Returns a DataFrame with columns: isin, stock_name, quantity_held, holding_percent, holding_value, report_date.
    """
    with get_session() as session:
        # Find the latest report_date for this fund
        latest_date = session.query(
            func.max(PortfolioBaseline.report_date)
        ).filter_by(fund_id=fund_id).scalar()

        if not latest_date:
            logger.warning("No baseline found for fund: %s", fund_id)
            return pd.DataFrame()

        rows = session.query(PortfolioBaseline).filter_by(
            fund_id=fund_id,
            report_date=latest_date,
        ).all()

        data = [{
            "isin": r.isin,
            "stock_name": r.stock_name,
            "quantity_held": r.quantity_held,
            "holding_percent": r.holding_percent,
            "holding_value": r.holding_value,
            "report_date": r.report_date,
        } for r in rows]

        return pd.DataFrame(data)


# ═══════════════════════════════════════════════════════════════════════════════
# Trade Ledger Operations
# ═══════════════════════════════════════════════════════════════════════════════

def insert_trade(
    fund_id: str,
    trade_date: date,
    transaction_type: str,
    quantity: int,
    exchange: str,
    source: str,
    isin: str = None,
    stock_name: str = None,
    symbol: str = None,
    execution_price: float = None,
    deal_type: str = None,
    raw_client_name: str = None,
) -> bool:
    """
    Insert a trade into the ledger. Returns True if inserted, False if duplicate.
    Deduplicates by fund_id + isin + trade_date + quantity + transaction_type + exchange.
    """
    with get_session() as session:
        # Check for duplicate
        existing = session.query(TradeLedger).filter_by(
            fund_id=fund_id,
            isin=isin,
            trade_date=trade_date,
            quantity=quantity,
            transaction_type=transaction_type,
            exchange=exchange,
        ).first()

        if existing:
            logger.debug("Duplicate trade skipped: %s %s %d %s", fund_id, isin, quantity, trade_date)
            return False

        trade_value = (quantity * execution_price) if execution_price else None

        session.add(TradeLedger(
            fund_id=fund_id,
            isin=isin,
            stock_name=stock_name,
            symbol=symbol,
            trade_date=trade_date,
            transaction_type=transaction_type.upper(),
            quantity=quantity,
            execution_price=execution_price,
            trade_value=trade_value,
            exchange=exchange.upper(),
            deal_type=deal_type,
            raw_client_name=raw_client_name,
            source=source,
        ))
        return True


def get_trades_since(fund_id: str, since_date: date) -> pd.DataFrame:
    """
    Fetch all trades for a fund after a given date.
    Returns a DataFrame sorted by trade_date.
    """
    with get_session() as session:
        rows = session.query(TradeLedger).filter(
            TradeLedger.fund_id == fund_id,
            TradeLedger.trade_date > since_date,
        ).order_by(TradeLedger.trade_date).all()

        data = [{
            "isin": r.isin,
            "stock_name": r.stock_name,
            "symbol": r.symbol,
            "trade_date": r.trade_date,
            "transaction_type": r.transaction_type,
            "quantity": r.quantity,
            "execution_price": r.execution_price,
            "trade_value": r.trade_value,
            "exchange": r.exchange,
            "deal_type": r.deal_type,
        } for r in rows]

        return pd.DataFrame(data)


def get_trade_count(fund_id: str = None) -> int:
    """Return total trades, optionally filtered by fund."""
    with get_session() as session:
        query = session.query(func.count(TradeLedger.trade_id))
        if fund_id:
            query = query.filter_by(fund_id=fund_id)
        return query.scalar()
