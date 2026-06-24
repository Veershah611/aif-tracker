"""
Data normalization utilities.

Handles the messy reality of Indian financial data:
  - Company name cleanup and standardization
  - Indian number format parsing ("14.0 Cr" → 140000000)
  - Quantity string cleanup (remove commas)
  - Whitespace and Unicode normalization
"""

import re
import unicodedata
from typing import Optional

from utils.logger import get_logger

logger = get_logger(__name__)


def normalize_text(text: str) -> str:
    """
    Clean and normalize a text string:
    - Strip leading/trailing whitespace
    - Collapse multiple spaces
    - Normalize Unicode to NFC form
    - Remove non-printable characters
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFC", str(text))
    text = re.sub(r"[^\S\n]+", " ", text)  # Collapse spaces (not newlines)
    text = text.strip()
    return text


def normalize_company_name(name: str) -> str:
    """
    Standardize a company name for consistent storage and matching.
    - Title case
    - Remove trailing "Ltd.", "Limited" variations and re-append as "Ltd."
    - Strip extra suffixes like "(BSE)", "(NSE)"
    """
    if not name:
        return ""

    name = normalize_text(name)

    # Remove exchange annotations
    name = re.sub(r"\s*\((?:BSE|NSE|SME|MAIN)\)\s*", "", name, flags=re.IGNORECASE)

    # Normalize "Limited" / "Ltd" / "Ltd." to "Ltd."
    name = re.sub(r"\s+Limited\.?\s*$", " Ltd.", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+Ltd\.?\s*$", " Ltd.", name, flags=re.IGNORECASE)

    # Title case but preserve common abbreviations
    words = name.split()
    result = []
    preserve_upper = {"Ltd.", "Ltd", "SME", "IPO", "LLP", "PVT", "BSE", "NSE", "ISIN", "AIF", "MF"}
    for word in words:
        if word.upper() in preserve_upper or word.endswith("."):
            result.append(word.upper() if word.upper() in preserve_upper else word)
        elif word.startswith("&"):
            result.append(word)
        else:
            result.append(word.title())
    name = " ".join(result)

    return name


def parse_indian_value(value_str: str) -> Optional[float]:
    """
    Parse Indian financial notation to raw float value.

    Examples:
        "14.0 Cr"   → 140000000.0
        "57.9 L"    → 5790000.0
        "3.5 Cr"    → 35000000.0
        "96.3 L"    → 9630000.0
        "1,05,00,000" → 10500000.0
        "2.4 Cr"    → 24000000.0
    """
    if not value_str:
        return None

    value_str = normalize_text(str(value_str))

    # Remove currency symbols
    value_str = value_str.replace("Rs", "").replace("₹", "").replace("?", "").strip()

    if not value_str or value_str == "-":
        return None

    # Check for Crore notation
    cr_match = re.match(r"([\d,.]+)\s*Cr", value_str, re.IGNORECASE)
    if cr_match:
        num = float(cr_match.group(1).replace(",", ""))
        return num * 10_000_000  # 1 Cr = 10 million

    # Check for Lakh notation
    l_match = re.match(r"([\d,.]+)\s*L(?:akh)?", value_str, re.IGNORECASE)
    if l_match:
        num = float(l_match.group(1).replace(",", ""))
        return num * 100_000  # 1 Lakh = 100,000

    # Try plain number (Indian comma format: 1,05,00,000)
    try:
        return float(value_str.replace(",", ""))
    except ValueError:
        logger.debug("Could not parse value: '%s'", value_str)
        return None


def parse_quantity(qty_str: str) -> Optional[int]:
    """
    Parse a quantity string to integer.
    Handles commas and decimal notation.

    Examples:
        "2,060,000" → 2060000
        "379200"    → 379200
        "1,23,000"  → 123000
        "379,200.00" → 379200
    """
    if not qty_str:
        return None

    qty_str = normalize_text(str(qty_str))
    qty_str = qty_str.replace(",", "")

    if not qty_str or qty_str == "-":
        return None

    try:
        return int(float(qty_str))
    except ValueError:
        logger.debug("Could not parse quantity: '%s'", qty_str)
        return None


def parse_percentage(pct_str: str) -> Optional[float]:
    """
    Parse a percentage string to float.

    Examples:
        "4.27%"  → 4.27
        "12.04"  → 12.04
        "1.82 %" → 1.82
    """
    if not pct_str:
        return None

    pct_str = normalize_text(str(pct_str))
    pct_str = pct_str.replace("%", "").strip()

    if not pct_str or pct_str == "-":
        return None

    try:
        return float(pct_str)
    except ValueError:
        logger.debug("Could not parse percentage: '%s'", pct_str)
        return None


def clean_symbol(symbol: str) -> str:
    """Clean an exchange symbol (uppercase, strip spaces)."""
    if not symbol:
        return ""
    return normalize_text(symbol).upper().strip()
