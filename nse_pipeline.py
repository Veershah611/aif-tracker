import requests
from datetime import datetime, date
import logging
from config.fund_registry import ALIAS_TO_FUND_ID
from database.operations import insert_trade
from scrapers.security_master import lookup_isin
from engine.fuzzy_matcher import match_fund

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s")
logger = logging.getLogger("nse_pipeline")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

def get_nse_large_deals():
    """Fetches large deals data from NSE bypassing bot protection."""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        logger.info("Establishing session with NSE (fetching cookies)...")
        session.get("https://www.nseindia.com", timeout=10)
        
        logger.info("Fetching Large Deals data from NSE...")
        api_url = "https://www.nseindia.com/api/snapshot-capital-market-largedeal"
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching NSE deals: {e}")
        return {}

def get_bse_bulk_deals():
    """Fetches bulk deals data from BSE."""
    session = requests.Session()
    session.headers.update(HEADERS)
    
    try:
        logger.info("Fetching Bulk Deals data from BSE...")
        api_url = "https://api.bseindia.com/BseIndiaAPI/api/BulkandBlockDeal/w?flag=bulk&fromdate=&todate="
        response = session.get(api_url, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching BSE deals: {e}")
        return {}

def process_and_update():
    """Processes deals and inserts matched ones into the database."""
    inserted_count = 0
    today = date.today()
    
    # 1. Process NSE
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
            qty = str(deal.get("quantity", "0")).replace(",", "")
            price = str(deal.get("tradePrice", "0")).replace(",", "")
            
            if action in ["BUY", "SELL"] and qty.isdigit():
                qty = int(qty)
                price = float(price) if price.replace(".", "").isdigit() else 0.0
                isin = lookup_isin(company_name=stock_name)
                
                success = insert_trade(
                    fund_id=fund_id,
                    stock_name=stock_name,
                    trade_date=today,
                    trade_type="BUY" if action == "BUY" else "SELL",
                    quantity=qty,
                    price=price,
                    exchange="NSE",
                    client_name=client_name,
                    isin=isin
                )
                if success:
                    inserted_count += 1
                    logger.info(f"NSE Match: {fund_id} {action} {qty} {stock_name}")

    # 2. Process BSE
    bse_data = get_bse_bulk_deals()
    bse_deals = bse_data.get("Data", []) if isinstance(bse_data, dict) else []
    for deal in bse_deals:
        client_name = deal.get("ClientName", "")
        fund_id = match_fund(client_name)
        if not fund_id:
            continue
        
        stock_name = deal.get("ScripName", "")
        action = deal.get("BuySell", "").upper()
        qty = str(deal.get("Quantity", "0")).replace(",", "")
        price = str(deal.get("Price", "0")).replace(",", "")
        
        if action in ["B", "S", "BUY", "SELL"] and qty.isdigit():
            trade_type = "BUY" if action in ["B", "BUY"] else "SELL"
            qty = int(qty)
            price = float(price) if price.replace(".", "").isdigit() else 0.0
            isin = lookup_isin(company_name=stock_name)
            
            success = insert_trade(
                fund_id=fund_id,
                stock_name=stock_name,
                trade_date=today,
                trade_type=trade_type,
                quantity=qty,
                price=price,
                exchange="BSE",
                client_name=client_name,
                isin=isin
            )
            if success:
                inserted_count += 1
                logger.info(f"BSE Match: {fund_id} {trade_type} {qty} {stock_name}")

    return {"NSE": inserted_count, "BSE": 0}

if __name__ == "__main__":
    process_and_update()
