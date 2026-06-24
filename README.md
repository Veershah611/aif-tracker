<<<<<<< HEAD
# AIF & Mutual Fund Portfolio Scraper

A complete Python scraping and portfolio reconstruction system for tracking 8 institutional funds (4 AIFs + 4 Mutual Funds) across Indian equity markets. 

The system implements a three-engine architecture to reconstruct current portfolios by taking quarterly baselines and applying daily transaction deltas.

## Features

- **Baseline Aggregator**: Playwright-based headless Chromium scraping of Trendlyne superstar shareholders.
- **Delta Engine**: Intercepts NSE/BSE bulk and block deal APIs with fuzzy matching for entity resolution.
- **AMC Parser**: Downloads and parses Mutual Fund portfolio Excel files directly from AMC websites (Quant, Bandhan, BOI).
- **Portfolio Reconstructor**: Calculates real-time portfolio holdings using the formula: `Current = Baseline + Buys - Sells`.
- **Automated Scheduling**: Configured with APScheduler to run jobs daily, monthly, and quarterly as required.

## Project Structure

```text
aif_scrapper/
├── config/
│   ├── settings.py              # URLs, thresholds, proxy config
│   └── fund_registry.py         # 8 funds + alias mappings
├── database/
│   ├── models.py                # 4 SQLAlchemy tables
│   ├── connection.py            # SQLite engine + session factory
│   └── operations.py            # CRUD with deduplication
├── engine/
│   ├── normalizer.py            # Indian number parsing (Cr/L)
│   ├── fuzzy_matcher.py         # RapidFuzz entity resolution
│   └── portfolio_reconstructor.py  # Current = Baseline + Deltas
├── scrapers/
│   ├── security_master.py       # BSE ISIN mapping
│   ├── baseline_aggregator.py   # Playwright + Trendlyne
│   ├── delta_engine.py          # NSE/BSE bulk/block APIs
│   └── amc_parser.py            # AMC Excel parser
├── utils/
│   ├── logger.py                # Dual console + file logging
│   └── http_client.py           # NSE/BSE sessions with anti-bot
├── main.py                      # CLI with 9 subcommands
├── scheduler.py                 # APScheduler (daily/monthly/quarterly)
├── requirements.txt
└── .env.example
```

## Setup & Installation

1. **Clone or navigate to the project directory**:
   ```bash
   cd c:\Users\Veer\Documents\projects\aif_scrapper
   ```

2. **Create and activate a virtual environment** (optional but recommended):
   ```bash
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Playwright browsers** (Required for the Baseline Aggregator):
   ```bash
   python -m playwright install chromium
   ```

5. **Configuration**:
   Copy the example environment file and adjust if necessary (e.g., adding proxies).
   ```bash
   cp .env.example .env
   ```

## Usage: CLI Commands

The system is managed via a central CLI (`main.py`).

| Command | Purpose |
|---|---|
| `python main.py init-db` | Create database tables and seed the 8 target funds |
| `python main.py list-funds` | Show all target funds configured in the registry |
| `python main.py update-securities` | Refresh ISIN master list from BSE |
| `python main.py scrape-baseline` | Scrape Trendlyne for AIF baselines |
| `python main.py scrape-deals` | Run the daily NSE/BSE delta engine (Bulk/Block deals) |
| `python main.py parse-amc` | Run the monthly Mutual Fund Excel parser |
| `python main.py portfolio --all` | Reconstruct and display all portfolios |
| `python main.py run-all` | Execute the full pipeline sequentially |
| `python main.py scheduler` | Start the automated background scheduler |

## How to Populate Data

To properly initialize the database with real data, run these commands in order:

1. **Initialize the database**:
   ```bash
   python main.py init-db
   ```
2. **Scrape AIF Baselines** (Requires Playwright):
   ```bash
   python main.py scrape-baseline
   ```
3. **Parse Mutual Fund Portfolios**:
   ```bash
   python main.py parse-amc
   ```
4. **Capture Daily Deals** (Run this daily after market close):
   ```bash
   python main.py scrape-deals
   ```

## Visual Dashboard (Frontend)

To make everything visible, the project includes a premium glassmorphism dark-mode UI built with FastAPI and React.

1. **Start the Backend API:**
   In one terminal, start the FastAPI server on port 8000:
   ```bash
   python -m uvicorn api:app --host 127.0.0.1 --port 8000
   ```

2. **Start the Frontend UI:**
   In another terminal, navigate to the frontend directory and start Vite:
   ```bash
   cd frontend
   npm run dev
   ```
   Open your browser to `http://localhost:5173` to view the dashboards and trade ledgers.

## Automated Scheduling

You can run the application as a continuous background service that triggers scrapers on a predefined schedule:
```bash
python main.py scheduler
```
* **Daily (17:30 IST)**: Delta Engine (NSE/BSE deals)
* **Monthly (7th @ 20:00 IST)**: AMC Mutual Fund Excel Parser
* **Quarterly (20th @ 20:00 IST)**: Baseline Aggregator (Trendlyne)
* **Weekly (Sun @ 02:00 IST)**: Security Master ISIN refresh

## Known Limitations

**NSE/BSE API Access:**
Both exchange APIs enforce aggressive anti-bot measures that frequently block standard `requests`-based sessions (returning 403 Forbidden or HTML error pages instead of JSON).

For production use, the Delta Engine may require:
1. Upgrading the NSE/BSE fetchers to use Playwright to intercept the API XHR calls from within a real browser context.
2. Utilizing rotating residential proxies (configurable in `.env` via `PROXY_POOL`).
3. As a fallback, scraping Trendlyne's bulk/block deal pages instead of querying the exchanges directly.
=======
# aif-tracker
It tracks and scrapes data for aifs
>>>>>>> 29d56429a31bcef9eab15a047ae59fe9ff023d35
