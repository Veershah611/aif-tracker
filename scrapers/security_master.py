"""
Security Master — ISIN ↔ Symbol ↔ Scrip Code mapping.

Per document §4.2:
  - Builds a local mapping table from the BSE master security list
  - Translates any symbol or scrip code to its definitive ISIN
  - Run weekly to keep mapping current
"""

import io
import json
from typing import Optional

import pandas as pd

from config.settings import BSE_SECURITY_MASTER_URL
from database.operations import bulk_upsert_securities, resolve_isin, get_security_count
from utils.http_client import BSESession, create_session
from utils.logger import get_logger

logger = get_logger(__name__)

# Alternative BSE URLs for equity list
BSE_EQUITY_CSV_URL = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Atea=&Flag=true"


def fetch_bse_security_list() -> pd.DataFrame:
    """
    Fetch the complete list of BSE-listed securities.
    Returns a DataFrame with columns: isin, company_name, scrip_code_bse, group_name, face_value, industry.
    """
    logger.info("Fetching BSE security master list...")
    session = BSESession()

    try:
        response = session.get(BSE_EQUITY_CSV_URL)
        data = response.json()

        if not data:
            logger.error("BSE security list returned empty data.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        logger.info("Fetched %d securities from BSE.", len(df))

        # BSE API returns columns like: Scrip_Code, SCRIP_NAME, ISIN_NUMBER, GROUP, FACE_VALUE, INDUSTRY
        # Column names may vary — normalize
        col_map = {}
        for col in df.columns:
            col_upper = col.upper().replace(" ", "_")
            if "ISIN" in col_upper:
                col_map[col] = "isin"
            elif "SCRIP_CODE" in col_upper or "SCRIPCODE" in col_upper or col_upper == "SCRIP_CD":
                col_map[col] = "scrip_code_bse"
            elif "SCRIP_NAME" in col_upper or "SCRIPNAME" in col_upper or "LONG_NAME" in col_upper or "SCRIP_N" in col_upper:
                col_map[col] = "company_name"
            elif "GROUP" in col_upper:
                col_map[col] = "group_name"
            elif "FACE" in col_upper:
                col_map[col] = "face_value"
            elif "INDUSTRY" in col_upper:
                col_map[col] = "industry"

        df = df.rename(columns=col_map)

        # Ensure required columns exist
        required = ["isin", "company_name"]
        for col in required:
            if col not in df.columns:
                logger.error("Missing required column '%s' in BSE data. Available: %s", col, list(df.columns))
                return pd.DataFrame()

        # Filter rows with valid ISINs
        df = df[df["isin"].notna() & (df["isin"].str.len() > 5)]

        # Clean scrip code
        if "scrip_code_bse" in df.columns:
            df["scrip_code_bse"] = df["scrip_code_bse"].astype(str)

        logger.info("Processed %d securities with valid ISINs.", len(df))
        return df

    except Exception as e:
        logger.error("Failed to fetch BSE security list: %s", e)
        return pd.DataFrame()


def update_security_master():
    """
    Fetch the BSE master list and upsert all securities into the database.
    This should be run weekly per document §4.2.
    """
    df = fetch_bse_security_list()

    if df.empty:
        logger.warning("No securities to update.")
        return 0

    records = []
    for _, row in df.iterrows():
        rec = {
            "isin": row.get("isin", ""),
            "company_name": row.get("company_name", ""),
        }
        if "scrip_code_bse" in row:
            rec["scrip_code_bse"] = str(row["scrip_code_bse"])
        if "group_name" in row:
            rec["group_name"] = str(row["group_name"])
        if "face_value" in row:
            try:
                rec["face_value"] = float(row["face_value"])
            except (ValueError, TypeError):
                pass
        if "industry" in row:
            rec["industry"] = str(row["industry"])

        records.append(rec)

    bulk_upsert_securities(records)
    total = get_security_count()
    logger.info("Security master updated. Total securities in database: %d", total)
    return len(records)


def lookup_isin(
    symbol: str = None,
    scrip_code: str = None,
    company_name: str = None,
) -> Optional[str]:
    """
    Convenience wrapper around database ISIN resolution.
    Tries symbol → scrip_code → company_name in order.
    """
    return resolve_isin(symbol=symbol, scrip_code=scrip_code, company_name=company_name)
