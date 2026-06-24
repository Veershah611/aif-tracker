from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import json
import math

from config.fund_registry import ALL_FUNDS, FUND_BY_ID
from engine.portfolio_reconstructor import reconstruct_all_portfolios
from database.connection import get_session
from database.models import TradeLedger

app = FastAPI(title="AIF Scraper API", version="1.0.0")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def clean_nan(obj: Any) -> Any:
    """Helper to replace NaN/Infinity values with None for JSON serialization."""
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(i) for i in obj]
    return obj

@app.get("/api/funds")
def get_funds() -> List[Dict[str, Any]]:
    """Get the list of all registered funds."""
    return [
        {
            "fund_id": fund.fund_id,
            "fund_name": fund.fund_name,
            "regulatory_type": fund.regulatory_type,
            "amc_scheme_name": fund.amc_scheme_name,
            "trendlyne_query": fund.trendlyne_query
        }
        for fund in ALL_FUNDS
    ]

@app.get("/api/portfolio/{fund_id}")
def get_portfolio(fund_id: str):
    """Get the reconstructed portfolio for a specific fund."""
    if fund_id not in FUND_BY_ID:
        raise HTTPException(status_code=404, detail="Fund not found")
        
    portfolios = reconstruct_all_portfolios()
    if fund_id not in portfolios:
        raise HTTPException(status_code=404, detail="No data available for this fund")
        
    df = portfolios[fund_id]
    
    # Fill NaN values with None for JSON compatibility
    df = df.where(df.notnull(), None)
    
    records = df.to_dict(orient="records")
    return clean_nan(records)

@app.get("/api/trades")
def get_recent_trades(limit: int = 50):
    """Get recent trades captured by the Delta Engine."""
    with get_session() as session:
        trades = session.query(TradeLedger).order_by(TradeLedger.trade_date.desc(), TradeLedger.trade_id.desc()).limit(limit).all()
        return [
            {
                "id": t.trade_id,
                "fund_id": t.fund_id,
                "isin": t.isin,
                "stock_name": t.stock_name,
                "symbol": t.symbol,
                "trade_date": t.trade_date.isoformat(),
                "transaction_type": t.transaction_type,
                "quantity": t.quantity,
                "execution_price": t.execution_price,
                "exchange": t.exchange,
                "deal_type": t.deal_type,
            }
            for t in trades
        ]

import pandas as pd

@app.get("/api/stocks")
def get_all_stocks():
    """Return all stock positions across all funds with fund names included."""
    portfolios = reconstruct_all_portfolios()
    
    fund_name_map = {f.fund_id: f.fund_name for f in ALL_FUNDS}
    
    all_dfs = []
    for fund_id, df in portfolios.items():
        if not df.empty:
            df = df.copy()
            df["fund_id"] = fund_id
            df["fund_name"] = fund_name_map.get(fund_id, fund_id)
            all_dfs.append(df)
            
    if not all_dfs:
        return []
        
    combined = pd.concat(all_dfs, ignore_index=True)
    
    # Sort by fund name, then by position size
    combined = combined.sort_values(["fund_name", "current_qty"], ascending=[True, False])
    
    combined = combined.where(combined.notnull(), None)
    records = combined.to_dict(orient="records")
    return clean_nan(records)
