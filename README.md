# AIF & Mutual Fund Portfolio Scraper

A complete Python scraping and portfolio reconstruction system for tracking 8 institutional funds (4 AIFs + 4 Mutual Funds) across Indian equity markets. 

The system implements a three-engine architecture to reconstruct current portfolios by taking quarterly baselines and applying daily transaction deltas.

## Features

- **Baseline Aggregator**: Playwright-based headless Chromium scraping of Trendlyne superstar shareholders.
- **Delta Engine**: Intercepts NSE/BSE bulk and block deal APIs with fuzzy matching for entity resolution.
- **AMC Parser**: Downloads and parses Mutual Fund portfolio Excel files directly from AMC websites (Quant, Bandhan, BOI).
- **Portfolio Reconstructor**: Calculates real-time portfolio holdings using the formula: `Current = Baseline + Buys - Sells`.
- **Serverless Automation**: Secured trigger endpoints meant to be hit by external crons (like GitHub Actions) to automate execution on free tiers.

## Modular Monolith Architecture

The codebase has been refactored to explicitly separate the Python backend and the React frontend.

```text
aif_scrapper/
├── backend/                     # Python Backend Environment
│   ├── app/                     
│   │   ├── api/                 # FastAPI routes and Trigger Endpoints
│   │   ├── core/                # Pydantic Configs, Logger, Registry
│   │   ├── db/                  # SQLAlchemy Models and Operations
│   │   ├── engine/              # Portfolio Reconstructor, Fuzzy Matcher
│   │   └── scrapers/            # Web Scrapers (Playwright, NSE/BSE APIs)
│   ├── main.py                  # FastAPI Application Entrypoint
│   ├── cli.py                   # Central CLI tool for manual data ops
│   ├── requirements.txt
│   └── pyproject.toml           # Ruff & Mypy config
├── frontend/                    # React + Vite Frontend
│   ├── src/                     # UI Components, Layout, Assets
│   ├── package.json             # ESLint, Prettier, Vite scripts
│   └── .eslintrc.cjs
├── .github/workflows/           # CI/CD & Automated Cron Actions
└── README.md
```

---

## How to Open and Run Locally

To run the project on your local machine, you need to spin up the API Backend and the React Frontend in two separate terminals.

### 1. Setup the Backend API

Open a terminal and navigate to the project root:

```bash
cd c:\Users\Veer\Documents\projects\aif_scrapper
```

Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
venv\Scripts\activate   # (On Windows)
```

Install the backend dependencies:
```bash
cd backend
pip install -r requirements.txt
python -m playwright install chromium --with-deps
```

Configure your environment:
1. Create `.env` inside `backend/` by copying the `.env.example`.
2. Add any proxies or specific database URLs if needed (Defaults to a local SQLite file).

Start the FastAPI Web Server:
```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

*Your API is now running locally at `http://localhost:8000`.*

### 2. Setup the Frontend UI

Open a **new, second terminal** and navigate to the frontend directory:

```bash
cd c:\Users\Veer\Documents\projects\aif_scrapper\frontend
```

Install Node.js dependencies:
```bash
npm install
```

Start the Vite development server:
```bash
npm run dev
```

*Open your browser and navigate to the URL provided in the terminal (usually `http://localhost:5173`).*

---

## Using the CLI (Manual Data Population)

While the frontend has a button to trigger the scrapers via the API, you can also run manual scrapes directly from the command line using the `cli.py` tool.

From the `backend/` directory:

| Command | Purpose |
|---|---|
| `python cli.py init-db` | Create database tables and seed the 8 target funds |
| `python cli.py list-funds` | Show all target funds configured in the registry |
| `python cli.py scrape-baseline` | Scrape Trendlyne for AIF baselines |
| `python cli.py scrape-deals` | Run the daily NSE/BSE delta engine (Bulk/Block deals) |
| `python cli.py parse-amc` | Run the monthly Mutual Fund Excel parser |

---

## Deployment Setup

This repository is optimized for a fully **Free-Tier Serverless Deployment**.

### 1. Render (Backend)
The backend is deployed manually via Render Web Services.
* In the Render dashboard, create a new "Web Service" from your GitHub repository.
* Set the **Root Directory** to `backend`.
* Set the **Build Command** to `pip install -r requirements.txt && playwright install chromium --with-deps`
* Set the **Start Command** to `uvicorn main:app --host 0.0.0.0 --port $PORT`
* Because the free tier spins down after 15 minutes of inactivity, we use external cron triggers instead of persistent background workers.

### 2. Vercel (Frontend)
The frontend is deployed to Vercel. 
* Set the Root Directory to `frontend`.
* Add `VITE_API_BASE_URL` pointing to your Render application (e.g., `https://aif-tracker.onrender.com/api`).

### 3. GitHub Actions (Automation)
Since there is no persistent background worker, the scraping tasks are automated using a GitHub Actions Scheduled Workflow (`.github/workflows/cron-scraper.yml`).
* It automatically sends an HTTP POST request to the Render API every Monday-Friday at 7:00 PM IST to run the Delta Engine.
* Ensure you add `RENDER_API_URL` to your GitHub Repository Secrets.
