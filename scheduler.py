"""
Automated scheduler for the AIF Scrapper pipeline.

Per document §6.3, schedule (all IST):
  - Daily 17:30     : Delta Engine (NSE + BSE bulk/block deals)
  - Monthly 5th-10th 20:00 : AMC Direct Parser
  - Quarterly 15th-25th 20:00 : Baseline Aggregator (Trendlyne)
  - Weekly Sunday 02:00 : Security Master refresh
"""

from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from utils.logger import get_logger

logger = get_logger("scheduler")


def job_delta_engine():
    """Daily: Fetch and process NSE/BSE bulk/block deals."""
    logger.info("SCHEDULER: Running Delta Engine...")
    from scrapers.delta_engine import run_delta_engine
    try:
        results = run_delta_engine()
        logger.info("SCHEDULER: Delta Engine complete. Results: %s", results)
    except Exception as e:
        logger.error("SCHEDULER: Delta Engine failed: %s", e, exc_info=True)


def job_amc_parser():
    """Monthly: Parse AMC Excel portfolios."""
    logger.info("SCHEDULER: Running AMC Parser...")
    from scrapers.amc_parser import run_amc_parser
    try:
        results = run_amc_parser()
        logger.info("SCHEDULER: AMC Parser complete. Results: %s", results)
    except Exception as e:
        logger.error("SCHEDULER: AMC Parser failed: %s", e, exc_info=True)


def job_baseline_aggregator():
    """Quarterly: Scrape Trendlyne for AIF baselines."""
    logger.info("SCHEDULER: Running Baseline Aggregator...")
    from scrapers.baseline_aggregator import scrape_all_baselines
    try:
        results = scrape_all_baselines()
        logger.info("SCHEDULER: Baseline Aggregator complete. Results: %s", results)
    except Exception as e:
        logger.error("SCHEDULER: Baseline Aggregator failed: %s", e, exc_info=True)


def job_security_master():
    """Weekly: Refresh ISIN security master from BSE."""
    logger.info("SCHEDULER: Updating Security Master...")
    from scrapers.security_master import update_security_master
    try:
        count = update_security_master()
        logger.info("SCHEDULER: Security Master updated. %d securities.", count)
    except Exception as e:
        logger.error("SCHEDULER: Security Master update failed: %s", e, exc_info=True)


def start_scheduler():
    """
    Start the blocking scheduler with all configured jobs.
    This function blocks forever — run it in the foreground or as a service.
    """
    scheduler = BlockingScheduler(timezone="Asia/Kolkata")

    # ── Daily at 17:30 IST: Delta Engine ──────────────────────────────────
    scheduler.add_job(
        job_delta_engine,
        CronTrigger(hour=17, minute=30, timezone="Asia/Kolkata"),
        id="delta_engine",
        name="Daily Delta Engine (NSE/BSE Bulk Deals)",
        misfire_grace_time=3600,
    )

    # ── Monthly 7th at 20:00 IST: AMC Parser ─────────────────────────────
    # Runs on the 7th of each month (within the 5th-10th window per doc)
    scheduler.add_job(
        job_amc_parser,
        CronTrigger(day=7, hour=20, minute=0, timezone="Asia/Kolkata"),
        id="amc_parser",
        name="Monthly AMC Portfolio Parser",
        misfire_grace_time=86400,
    )

    # ── Quarterly 20th at 20:00 IST: Baseline Aggregator ─────────────────
    # Runs on the 20th of Jan, Apr, Jul, Oct (within 15th-25th window)
    scheduler.add_job(
        job_baseline_aggregator,
        CronTrigger(month="1,4,7,10", day=20, hour=20, minute=0, timezone="Asia/Kolkata"),
        id="baseline_aggregator",
        name="Quarterly Baseline Aggregator (Trendlyne)",
        misfire_grace_time=86400,
    )

    # ── Weekly Sunday at 02:00 IST: Security Master ───────────────────────
    scheduler.add_job(
        job_security_master,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="Asia/Kolkata"),
        id="security_master",
        name="Weekly Security Master Refresh",
        misfire_grace_time=86400,
    )

    logger.info("=" * 60)
    logger.info("AIF SCRAPPER SCHEDULER STARTED")
    logger.info("=" * 60)
    logger.info("Scheduled jobs:")
    for job in scheduler.get_jobs():
        logger.info("  • %s [%s]", job.name, job.trigger)
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop.")

    print("\nScheduler running. Jobs:")
    for job in scheduler.get_jobs():
        print(f"  • {job.name} — {job.trigger}")
    print("\nPress Ctrl+C to stop.\n")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        logger.info("Scheduler stopped by user.")
        print("\nScheduler stopped.")


if __name__ == "__main__":
    start_scheduler()
