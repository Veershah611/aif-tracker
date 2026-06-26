"""
Baseline Aggregator — Trendlyne Superstar Shareholders Scraper.

Per document §3.1:
  - Uses Playwright (headless Chromium) to scrape Trendlyne
  - Waits for dynamic JS rendering of .table DOM elements
  - Parses HTML tables with BeautifulSoup
  - Extracts: Stock Name, Quantity Held, Holding %, Holding Value
  - Stores in Portfolio_Baseline table

Runs quarterly for AIFs (15th-25th of quarter-end month).
"""

import asyncio
from datetime import date, datetime
from typing import List, Dict, Optional

from bs4 import BeautifulSoup
import pandas as pd

from app.core.config import TRENDLYNE_SUPERSTAR_URL, TRENDLYNE_BASE_URL
from app.core.fund_registry import AIF_FUNDS, ALL_FUNDS, FundConfig, FUND_BY_ID
from app.db.operations import upsert_baseline, bulk_upsert_baselines
from app.engine.normalizer import (
    normalize_company_name, parse_quantity,
    parse_percentage, parse_indian_value, normalize_text,
)
from app.scrapers.security_master import lookup_isin
from app.core.logger import get_logger

logger = get_logger(__name__)


def _get_current_quarter_end() -> date:
    """Get the end date of the current quarter."""
    today = date.today()
    quarter = (today.month - 1) // 3
    quarter_ends = [
        date(today.year, 3, 31),
        date(today.year, 6, 30),
        date(today.year, 9, 30),
        date(today.year, 12, 31),
    ]
    # Return the most recent quarter end
    for qe in reversed(quarter_ends):
        if qe <= today:
            return qe
    return quarter_ends[-1].replace(year=today.year - 1)


async def _scrape_trendlyne_page(url: str, fund_name: str) -> List[Dict]:
    """
    Use Playwright to scrape a single Trendlyne superstar shareholders page.

    Returns a list of dicts with keys:
        stock_name, quantity_held, holding_percent, holding_value
    """
    from playwright.async_api import async_playwright

    records = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
        )

        page = await context.new_page()

        try:
            logger.info("Navigating to Trendlyne: %s", url)
            await page.goto(url, wait_until="networkidle", timeout=60000)

            # Wait for the shareholding table to render
            # Trendlyne uses dynamic JS (Highcharts) — need to wait for table elements
            try:
                await page.wait_for_selector(
                    "table, .table-responsive, [class*='table']",
                    timeout=30000,
                )
                logger.info("Table element detected on page.")
            except Exception:
                logger.warning("No table element found. Trying alternative selectors...")
                # Try waiting for any data content
                await page.wait_for_timeout(5000)

            # Get the full rendered HTML
            html = await page.content()

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, "lxml")
            tables = soup.find_all("table")

            if not tables:
                logger.warning("No tables found on page for %s", fund_name)
                # Try finding data in div-based layouts
                await page.wait_for_timeout(3000)
                html = await page.content()
                soup = BeautifulSoup(html, "lxml")
                tables = soup.find_all("table")

            for table in tables:
                rows = table.find_all("tr")
                if len(rows) < 2:
                    continue

                # Detect header row
                header_row = rows[0]
                headers = [th.get_text(strip=True).lower() for th in header_row.find_all(["th", "td"])]

                # Identify columns by header text
                name_col = None
                qty_col = None
                pct_col = None
                val_col = None

                for i, h in enumerate(headers):
                    if name_col is None and any(kw in h for kw in ["stock", "company", "security"]):
                        name_col = i
                    elif name_col is None and "name" in h and "investor" not in h and "client" not in h:
                        name_col = i
                    elif qty_col is None and any(kw in h for kw in ["quantity", "qty", "shares"]):
                        qty_col = i
                    elif pct_col is None and any(kw in h for kw in ["holding %", "percent", "%", "holding"]):
                        pct_col = i
                    elif val_col is None and any(kw in h for kw in ["value", "amount", "worth"]):
                        val_col = i

                if name_col is None:
                    # Try positional fallback: name is usually first column
                    if len(headers) >= 3:
                        name_col = 0
                        pct_col = 1
                        qty_col = 2
                        val_col = 3 if len(headers) > 3 else None

                if name_col is None:
                    continue

                # Parse data rows
                for row in rows[1:]:
                    cells = row.find_all(["td", "th"])
                    if len(cells) <= name_col:
                        continue

                    stock_name = normalize_text(cells[name_col].get_text(strip=True))
                    if not stock_name or stock_name.lower() in ["total", "grand total", ""]:
                        continue

                    record = {"stock_name": normalize_company_name(stock_name)}

                    if qty_col is not None and qty_col < len(cells):
                        record["quantity_held"] = parse_quantity(cells[qty_col].get_text(strip=True))

                    if pct_col is not None and pct_col < len(cells):
                        record["holding_percent"] = parse_percentage(cells[pct_col].get_text(strip=True))

                    if val_col is not None and val_col < len(cells):
                        record["holding_value"] = parse_indian_value(cells[val_col].get_text(strip=True))

                    # Only include records with at least a name and quantity
                    if record.get("quantity_held"):
                        records.append(record)

            logger.info(
                "Extracted %d holdings for %s from Trendlyne.",
                len(records), fund_name
            )

        except Exception as e:
            logger.error("Error scraping Trendlyne for %s: %s", fund_name, e)

        finally:
            await browser.close()

    return records


def scrape_fund_baseline(fund: FundConfig, report_date: date = None) -> int:
    """
    Scrape the baseline portfolio for a single fund from Trendlyne.
    Returns the number of holdings extracted.
    """
    if report_date is None:
        report_date = _get_current_quarter_end()

    url = f"{TRENDLYNE_SUPERSTAR_URL}?query={fund.trendlyne_query}"
    logger.info("Scraping baseline for %s (report_date=%s)", fund.fund_name, report_date)

    # Run the async scraper
    records = asyncio.run(_scrape_trendlyne_page(url, fund.fund_name))

    if not records:
        logger.warning("No holdings extracted for %s", fund.fund_name)
        return 0

    # Enrich records with ISIN resolution and store in database
    stored = 0
    for rec in records:
        isin = lookup_isin(company_name=rec["stock_name"])

        upsert_baseline(
            fund_id=fund.fund_id,
            stock_name=rec["stock_name"],
            quantity_held=rec.get("quantity_held", 0),
            report_date=report_date,
            source="trendlyne",
            isin=isin,
            holding_percent=rec.get("holding_percent"),
            holding_value=rec.get("holding_value"),
        )
        stored += 1

    logger.info("Stored %d baseline holdings for %s.", stored, fund.fund_name)
    return stored


def scrape_all_baselines(report_date: date = None) -> dict:
    """
    Scrape baseline portfolios for all AIF funds.
    Returns dict of {fund_id: count_of_holdings}.
    """
    results = {}
    for fund in ALL_FUNDS:
        try:
            count = scrape_fund_baseline(fund, report_date)
            results[fund.fund_id] = count
        except Exception as e:
            logger.error("Failed to scrape baseline for %s: %s", fund.fund_name, e)
            results[fund.fund_id] = 0

    logger.info("Baseline scraping complete: %s", results)
    return results
