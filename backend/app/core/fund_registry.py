"""
Fund Registry — Metadata, alias mappings, and Trendlyne query strings
for all 8 target funds (4 AIFs + 4 Mutual Funds).

Alias lists are sourced from document §4.1 and historical exchange filings.
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class FundConfig:
    """Configuration for a single target fund."""
    fund_id: str
    fund_name: str
    regulatory_type: str        # "AIF" or "MF"
    category: str               # e.g. "Category III", "Small Cap", "Value"
    aliases: List[str]          # Known exchange/filing name variants
    trendlyne_query: str        # URL query param for superstar-shareholders
    trendlyne_deals_query: str  # URL query param for bulk-block-deals
    amc_scheme_name: Optional[str] = None   # For MFs: scheme name in Excel
    amc_url: Optional[str] = None           # For MFs: direct disclosure URL


# ═══════════════════════════════════════════════════════════════════════════════
# AIF Fund Definitions
# ═══════════════════════════════════════════════════════════════════════════════

NEXUS_EQUITY = FundConfig(
    fund_id="nexus_equity",
    fund_name="Nexus Equity Growth Fund",
    regulatory_type="AIF",
    category="Category III",
    aliases=[
        "Nexus Equity Growth Fund",
        "Nexus Equity Growth Fund Sch-1",
        "Nexus Equity Growth Fund Sch 1",
        "Nexus Equity Growth Fun",
        "NEXUS EQUITY GROWTH FUND SCH-1",
        "NEXUS EQUITY GROWTH FUND",
        "Nexus Equity Growth Fund SCH-1",
    ],
    trendlyne_query="nexus%20equity%20growth%20fund%20sch%201",
    trendlyne_deals_query="NEXUS%20EQUITY%20GROWTH%20FUND%20SCH-1",
)

NEOMILE_GROWTH = FundConfig(
    fund_id="neomile_growth",
    fund_name="Neomile Growth Fund - Series I",
    regulatory_type="AIF",
    category="Category III",
    aliases=[
        "Neomile Growth Fund - Series I",
        "Neomile Growth Fund Series I",
        "Neomile Growth Fund- Series -I",
        "NEOMILE GROWTH FUND-SERIES I",
        "NEOMILE GROWTH FUND - SERIES I",
        "Neomile Growth Fund - Series 1",
        "Neomile Corporate Advisory Private Limited",
    ],
    trendlyne_query="neomile%20growth%20fund%20series%20i",
    trendlyne_deals_query="NEOMILE%20GROWTH%20FUND%20-%20SERIES%20I",
)

NEGEN_VALUE = FundConfig(
    fund_id="negen_value",
    fund_name="Negen Undiscovered Value Fund",
    regulatory_type="AIF",
    category="Category III",
    aliases=[
        "Negen Undiscovered Value Fund",
        "NEGEN UNDISCOVERED VALUE FUND",
        "Negen undiscovered value fund",
        "Negen Capital Services Pvt Ltd",
        "NEGEN CAPITAL SERVICES PVT LTD",
    ],
    trendlyne_query="NEGEN%20UNDISCOVERED%20VALUE%20FUND",
    trendlyne_deals_query="NEGEN%20UNDISCOVERED%20VALUE%20FUND",
)

AARTH_AIF = FundConfig(
    fund_id="aarth_aif",
    fund_name="Aarth AIF Growth Fund",
    regulatory_type="AIF",
    category="Category III",
    aliases=[
        "Aarth AIF Growth Fund",
        "Aarth Aif Growth Fund",
        "AARTH.AIF GROWTH FUND",
        "AARTH.AIF",
        "Aarth aif growth fund",
        "AARTH AIF GROWTH FUND",
        "Aarth AIF",
    ],
    trendlyne_query="aarth%20aif%20growth%20fund",
    trendlyne_deals_query="aarth%20aif",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Mutual Fund Definitions
# ═══════════════════════════════════════════════════════════════════════════════

QUANT_SMALL_CAP = FundConfig(
    fund_id="quant_small_cap",
    fund_name="Quant Small Cap Fund",
    regulatory_type="MF",
    category="Small Cap",
    aliases=[
        "Quant Small Cap Fund",
        "quant Small Cap Fund",
        "QUANT SMALL CAP FUND",
    ],
    trendlyne_query="quant%20mutual%20fund%20quant%20small%20cap%20fund",
    trendlyne_deals_query="quant%20mutual%20fund%20quant%20small%20cap%20fund",
    amc_scheme_name="quant Small Cap Fund",
    amc_url="https://quantmutual.com/statutory-disclosures",
)

BANDHAN_SMALL_CAP = FundConfig(
    fund_id="bandhan_small_cap",
    fund_name="Bandhan Small Cap Fund",
    regulatory_type="MF",
    category="Small Cap",
    aliases=[
        "Bandhan Small Cap Fund",
        "BANDHAN SMALL CAP FUND",
        "Bandhan Small Cap Fund - Regular Plan",
    ],
    trendlyne_query="bandhan%20small%20cap%20fund",
    trendlyne_deals_query="bandhan%20small%20cap%20fund",
    amc_scheme_name="Bandhan Small Cap Fund",
    amc_url="https://cmsnew.bandhanmutual.com/category/portfolio/monthly-portfolio/",
)

BANDHAN_VALUE = FundConfig(
    fund_id="bandhan_value",
    fund_name="Bandhan Value Fund",
    regulatory_type="MF",
    category="Value",
    aliases=[
        "Bandhan Value Fund",
        "BANDHAN VALUE FUND",
        "Bandhan Value Fund - Regular Plan",
    ],
    trendlyne_query="bandhan%20value%20fund",
    trendlyne_deals_query="bandhan%20value%20fund",
    amc_scheme_name="Bandhan Value Fund",
    amc_url="https://cmsnew.bandhanmutual.com/category/portfolio/monthly-portfolio/",
)

BOI_SMALL_CAP = FundConfig(
    fund_id="boi_small_cap",
    fund_name="Bank of India Small Cap Fund",
    regulatory_type="MF",
    category="Small Cap",
    aliases=[
        "Bank of India Small Cap Fund",
        "BOI Small Cap Fund",
        "BANK OF INDIA SMALL CAP FUND",
    ],
    trendlyne_query="bank%20of%20india%20small%20cap%20fund",
    trendlyne_deals_query="bank%20of%20india%20small%20cap%20fund",
    amc_scheme_name="Bank of India Small Cap Fund",
    amc_url="https://www.boimf.in/docs/default-source/investorcorner/monthly-portfolio/",
)

QUANT_MF = FundConfig(
    fund_id="quant_mf",
    fund_name="Quant Mutual Fund",
    regulatory_type="MF",
    category="Multi Scheme",
    aliases=[
        "Quant Mutual Fund",
        "quant mutual fund",
        "QUANT MUTUAL FUND",
        "Quant Mutual Fund -",
        "QUANT MUTUAL FUND -",
    ],
    trendlyne_query="quant%20mutual%20fund",
    trendlyne_deals_query="quant%20mutual%20fund",
    amc_scheme_name="Quant Mutual Fund",
    amc_url="https://quantmutual.com/statutory-disclosures",
)


# ═══════════════════════════════════════════════════════════════════════════════
# Master Registry
# ═══════════════════════════════════════════════════════════════════════════════

# All target funds as a list
ALL_FUNDS: List[FundConfig] = [
    NEXUS_EQUITY,
    NEOMILE_GROWTH,
    NEGEN_VALUE,
    AARTH_AIF,
    QUANT_SMALL_CAP,
    BANDHAN_SMALL_CAP,
    BANDHAN_VALUE,
    BOI_SMALL_CAP,
    QUANT_MF,
]

# Quick lookup by fund_id
FUND_BY_ID = {f.fund_id: f for f in ALL_FUNDS}

# AIF-only and MF-only subsets
AIF_FUNDS = [f for f in ALL_FUNDS if f.regulatory_type == "AIF"]
MF_FUNDS = [f for f in ALL_FUNDS if f.regulatory_type == "MF"]

# Flattened alias → fund_id mapping for fast lookups
# (exact match dictionary — fuzzy matching is handled by engine/fuzzy_matcher.py)
ALIAS_TO_FUND_ID = {}
for fund in ALL_FUNDS:
    for alias in fund.aliases:
        ALIAS_TO_FUND_ID[alias.upper()] = fund.fund_id
