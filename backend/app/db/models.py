"""
SQLAlchemy ORM models for the AIF Scrapper database.

Tables per document §6.2:
  - Entity          : Fund metadata
  - SecurityMaster  : ISIN ↔ Symbol ↔ Scrip Code mapping
  - PortfolioBaseline : Quarterly/monthly portfolio snapshots
  - TradeLedger     : Daily bulk/block deal records
"""

from datetime import date, datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Date, DateTime,
    ForeignKey, UniqueConstraint, Index, Text,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all models."""
    pass


class Entity(Base):
    """
    Stores metadata for each target fund.
    Seeded from config/fund_registry.py on init-db.
    """
    __tablename__ = "entities"

    fund_id = Column(String(50), primary_key=True)
    fund_name = Column(String(200), nullable=False)
    regulatory_type = Column(String(10), nullable=False)   # "AIF" or "MF"
    category = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    baselines = relationship("PortfolioBaseline", back_populates="entity")
    trades = relationship("TradeLedger", back_populates="entity")

    def __repr__(self):
        return f"<Entity({self.fund_id}: {self.fund_name})>"


class SecurityMaster(Base):
    """
    Master mapping of ISIN ↔ NSE Symbol ↔ BSE Scrip Code.
    Refreshed weekly from BSE equity list.
    Acts as the single source of truth for equity identification (§4.2).
    """
    __tablename__ = "security_master"

    isin = Column(String(20), primary_key=True)
    symbol_nse = Column(String(30), index=True)
    scrip_code_bse = Column(String(20), index=True)
    company_name = Column(String(300), nullable=False)
    group_name = Column(String(10))         # BSE group (A, B, T, etc.)
    face_value = Column(Float)
    industry = Column(String(200))
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Security({self.isin}: {self.company_name})>"


class PortfolioBaseline(Base):
    """
    Archives the official, historical portfolio snapshots.
    - For AIFs: populated by Trendlyne scraper (quarterly)
    - For MFs: populated by AMC Excel parser (monthly)
    """
    __tablename__ = "portfolio_baseline"

    baseline_id = Column(Integer, primary_key=True, autoincrement=True)
    fund_id = Column(String(50), ForeignKey("entities.fund_id"), nullable=False)
    isin = Column(String(20), index=True)       # May be null if ISIN unresolved
    stock_name = Column(String(300), nullable=False)
    quantity_held = Column(Integer, nullable=False)
    holding_percent = Column(Float)
    holding_value = Column(Float)                # In INR
    report_date = Column(Date, nullable=False)   # Quarter-end or month-end date
    source = Column(String(50), nullable=False)  # "trendlyne", "amc_quant", "amc_bandhan", "amc_boi"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Deduplication: one record per fund + stock + report period
    __table_args__ = (
        UniqueConstraint("fund_id", "stock_name", "report_date", name="uq_baseline_fund_stock_date"),
        Index("ix_baseline_fund_date", "fund_id", "report_date"),
    )

    # Relationships
    entity = relationship("Entity", back_populates="baselines")

    def __repr__(self):
        return f"<Baseline({self.fund_id}/{self.stock_name} @ {self.report_date})>"


class TradeLedger(Base):
    """
    Operational heart of the Delta Engine.
    Stores every intercepted bulk/block deal matched to a target fund.
    """
    __tablename__ = "trade_ledger"

    trade_id = Column(Integer, primary_key=True, autoincrement=True)
    fund_id = Column(String(50), ForeignKey("entities.fund_id"), nullable=False)
    isin = Column(String(20), index=True)
    stock_name = Column(String(300))
    symbol = Column(String(30))                  # NSE symbol or BSE scrip
    trade_date = Column(Date, nullable=False)
    transaction_type = Column(String(4), nullable=False)  # "BUY" or "SELL"
    quantity = Column(Integer, nullable=False)
    execution_price = Column(Float)              # Weighted average trade price
    trade_value = Column(Float)                  # quantity * price
    exchange = Column(String(5), nullable=False) # "NSE" or "BSE"
    deal_type = Column(String(10))               # "BULK", "BLOCK", "SHORT"
    raw_client_name = Column(Text)               # Original name from API
    source = Column(String(50), nullable=False)  # "nse_api", "bse_api", "trendlyne"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Deduplication: prevent duplicate deal entries
    __table_args__ = (
        UniqueConstraint(
            "fund_id", "isin", "trade_date", "quantity",
            "transaction_type", "exchange",
            name="uq_trade_dedup"
        ),
        Index("ix_trade_fund_date", "fund_id", "trade_date"),
        Index("ix_trade_ledger_isin_date", "isin", "trade_date"),
    )

    # Relationships
    entity = relationship("Entity", back_populates="trades")

    def __repr__(self):
        return f"<Trade({self.fund_id} {self.transaction_type} {self.quantity} {self.stock_name} @ {self.trade_date})>"
