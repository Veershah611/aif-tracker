"""
Application settings and configuration constants.
Loads values from .env file with sensible defaults.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"
DOWNLOADS_DIR = DATA_DIR / "downloads"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
DOWNLOADS_DIR.mkdir(exist_ok=True)

# ─── Database ────────────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{DATA_DIR / 'aif_scrapper.db'}"
)

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "aif_scrapper.log"))

# ─── Fuzzy Matching ──────────────────────────────────────────────────────────
FUZZY_MATCH_THRESHOLD = int(os.getenv("FUZZY_MATCH_THRESHOLD", "85"))

# ─── HTTP / Anti-Bot ─────────────────────────────────────────────────────────
REQUEST_DELAY_MIN = float(os.getenv("REQUEST_DELAY_MIN", "2"))
REQUEST_DELAY_MAX = float(os.getenv("REQUEST_DELAY_MAX", "5"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
BACKOFF_FACTOR = 2  # Exponential backoff multiplier

# Proxy pool (comma-separated list of proxy URLs)
_proxy_raw = os.getenv("PROXY_POOL", "")
PROXY_POOL = [p.strip() for p in _proxy_raw.split(",") if p.strip()]

# Realistic browser User-Agent strings for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

# ─── NSE API ─────────────────────────────────────────────────────────────────
NSE_BASE_URL = "https://www.nseindia.com"
NSE_HOMEPAGE = NSE_BASE_URL
NSE_LARGE_DEAL_API = f"{NSE_BASE_URL}/api/snapshot-capital-market-largedeal"

# --- BSE API ----------------------------------------------------------------
BSE_BASE_URL = "https://api.bseindia.com/BseIndiaAPI/api"
BSE_BULK_DEAL_URL = f"{BSE_BASE_URL}/BulkandBlockDeal/w?flag=bulk&fromdate=&todate="
BSE_BLOCK_DEAL_URL = f"{BSE_BASE_URL}/BulkandBlockDeal/w?flag=block&fromdate=&todate="
BSE_EQUITY_LIST_URL = f"{BSE_BASE_URL}/ListofScripData/w?Group=&Atea=&Flag=true"
BSE_HOMEPAGE = "https://www.bseindia.com"

# ─── Trendlyne ───────────────────────────────────────────────────────────────
TRENDLYNE_BASE_URL = "https://trendlyne.com"
TRENDLYNE_SUPERSTAR_URL = f"{TRENDLYNE_BASE_URL}/portfolio/superstar-shareholders/custom/"
TRENDLYNE_BULK_BLOCK_URL = f"{TRENDLYNE_BASE_URL}/portfolio/bulk-block-deals/custom/"

# ─── AMC Disclosure URLs ─────────────────────────────────────────────────────
QUANT_MF_DISCLOSURES = "https://quantmutual.com/statutory-disclosures"
BANDHAN_MF_PORTFOLIO = "https://cmsnew.bandhanmutual.com/category/portfolio/monthly-portfolio/"
BOI_MF_DISCLOSURES = "https://www.boimf.in/docs/default-source/investorcorner/monthly-portfolio/"

# ─── BSE Security Master ────────────────────────────────────────────────────
BSE_SECURITY_MASTER_URL = "https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w?Group=&Atea=&Flag=true"
