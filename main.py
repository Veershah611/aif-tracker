"""
AIF Scrapper -- Main CLI Entry Point.

Commands:
    python main.py init-db                     Create tables and seed funds
    python main.py update-securities           Refresh ISIN security master
    python main.py scrape-baseline             Scrape Trendlyne for AIF & MF baselines
    python main.py scrape-deals                Run daily NSE/BSE delta engine (via nse_pipeline)
    python main.py portfolio <fund_id>         Show reconstructed portfolio
    python main.py portfolio --all             Show all fund portfolios
    python main.py run-all                     Execute full pipeline
    python main.py list-funds                  List all target funds
    python main.py scheduler                   Start the automated scheduler
"""

import argparse
import sys

from utils.logger import get_logger

logger = get_logger("main")


def cmd_init_db(args):
    """Initialize database tables and seed fund entities."""
    from database.connection import init_db
    init_db()
    print("[OK] Database initialized successfully.")


def cmd_update_securities(args):
    """Refresh the security master table from BSE."""
    from scrapers.security_master import update_security_master
    count = update_security_master()
    print(f"[OK] Security master updated. {count} securities processed.")


def cmd_scrape_baseline(args):
    """Scrape Trendlyne for AIF baseline portfolios."""
    from scrapers.baseline_aggregator import scrape_all_baselines, scrape_fund_baseline
    from config.fund_registry import FUND_BY_ID

    if args.fund:
        fund = FUND_BY_ID.get(args.fund)
        if not fund:
            print(f"[FAIL] Unknown fund: {args.fund}")
            print(f"  Available: {', '.join(FUND_BY_ID.keys())}")
            return
        count = scrape_fund_baseline(fund)
        print(f"[OK] Scraped {count} holdings for {fund.fund_name}.")
    else:
        results = scrape_all_baselines()
        print("[OK] Baseline scraping complete:")
        for fund_id, count in results.items():
            print(f"  {fund_id}: {count} holdings")


def cmd_scrape_deals(args):
    """Run the daily Delta Engine (NSE + BSE bulk/block deals)."""
    from nse_pipeline import process_and_update
    results = process_and_update()
    total = sum(results.values())
    print(f"[OK] Delta engine complete. {total} new matched deals.")
    for exchange, count in results.items():
        print(f"  {exchange.upper()}: {count} deals")





def cmd_portfolio(args):
    """Show reconstructed portfolio for one or all funds."""
    from engine.portfolio_reconstructor import display_portfolio, reconstruct_all_portfolios
    from config.fund_registry import ALL_FUNDS

    if args.all:
        portfolios = reconstruct_all_portfolios()
        for fund_id, df in portfolios.items():
            display_portfolio(fund_id)
    elif args.fund:
        display_portfolio(args.fund)
    else:
        print("Please specify --fund <fund_id> or --all")
        print(f"Available funds: {', '.join(f.fund_id for f in ALL_FUNDS)}")


def cmd_list_funds(args):
    """List all target funds."""
    from config.fund_registry import ALL_FUNDS
    print(f"\n{'=' * 70}")
    print(f"  {'Fund ID':<25} {'Name':<35} {'Type'}")
    print(f"{'=' * 70}")
    for fund in ALL_FUNDS:
        print(f"  {fund.fund_id:<25} {fund.fund_name:<35} {fund.regulatory_type}")
    print()


def cmd_run_all(args):
    """Execute the complete pipeline in order."""
    print("=" * 60)
    print("  FULL PIPELINE EXECUTION")
    print("=" * 60)

    # Step 1: Init DB
    print("\n[1/5] Initializing database...")
    cmd_init_db(args)

    # Step 2: Update security master
    print("\n[2/5] Updating security master...")
    try:
        cmd_update_securities(args)
    except Exception as e:
        print(f"  [WARN] Security master update failed: {e}")

    # Step 3: Scrape baselines
    print("\n[3/5] Scraping AIF baselines from Trendlyne...")
    try:
        cmd_scrape_baseline(args)
    except Exception as e:
        print(f"  [WARN] Baseline scraping failed: {e}")



    # Step 4: Run delta engine
    print("\n[4/4] Running delta engine (NSE + BSE deals)...")
    try:
        cmd_scrape_deals(args)
    except Exception as e:
        print(f"  [WARN] Delta engine failed: {e}")

    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)

    # Show all portfolios
    print("\nReconstructed portfolios:")
    args.all = True
    args.fund = None
    cmd_portfolio(args)


def cmd_scheduler(args):
    """Start the automated scheduler."""
    from scheduler import start_scheduler
    start_scheduler()


def main():
    parser = argparse.ArgumentParser(
        description="AIF Scrapper -- Automated AIF & Mutual Fund Portfolio Extraction",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # init-db
    subparsers.add_parser("init-db", help="Initialize database and seed funds")

    # update-securities
    subparsers.add_parser("update-securities", help="Refresh ISIN security master from BSE")

    # scrape-baseline
    baseline_parser = subparsers.add_parser("scrape-baseline", help="Scrape Trendlyne for AIF baselines")
    baseline_parser.add_argument("--fund", type=str, help="Specific fund_id to scrape (default: all AIFs)")

    # scrape-deals
    subparsers.add_parser("scrape-deals", help="Run daily NSE/BSE delta engine")



    # portfolio
    port_parser = subparsers.add_parser("portfolio", help="Show reconstructed portfolio")
    port_parser.add_argument("--fund", type=str, help="Fund ID to display")
    port_parser.add_argument("--all", action="store_true", help="Show all fund portfolios")

    # list-funds
    subparsers.add_parser("list-funds", help="List all target funds")

    # run-all
    subparsers.add_parser("run-all", help="Execute full pipeline")

    # scheduler
    subparsers.add_parser("scheduler", help="Start automated scheduler")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "init-db": cmd_init_db,
        "update-securities": cmd_update_securities,
        "scrape-baseline": cmd_scrape_baseline,
        "scrape-deals": cmd_scrape_deals,
        "portfolio": cmd_portfolio,
        "list-funds": cmd_list_funds,
        "run-all": cmd_run_all,
        "scheduler": cmd_scheduler,
    }

    handler = commands.get(args.command)
    if handler:
        try:
            handler(args)
        except KeyboardInterrupt:
            print("\nInterrupted.")
            sys.exit(0)
        except Exception as e:
            logger.error("Command '%s' failed: %s", args.command, e, exc_info=True)
            print(f"\n[FAIL] Error: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
