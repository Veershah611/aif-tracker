from fastapi import APIRouter, BackgroundTasks

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("triggers")
trigger_router = APIRouter()

@trigger_router.post("/trigger/delta-engine")
async def trigger_delta_engine(
    background_tasks: BackgroundTasks
):
    """Trigger the daily NSE/BSE delta engine."""
    
    from app.scrapers.nse_pipeline import process_and_update
    
    # Run the heavy scraping task in the background so the HTTP request completes quickly
    background_tasks.add_task(process_and_update)
    logger.info("Delta Engine trigger received. Task enqueued.")
    
    return {"status": "ok", "message": "Delta Engine started in background."}

@trigger_router.post("/trigger/baseline-aggregator")
async def trigger_baseline_aggregator(
    background_tasks: BackgroundTasks
):
    """Trigger the quarterly baseline aggregator (Trendlyne)."""
    
    from app.scrapers.baseline_aggregator import scrape_all_baselines
    
    background_tasks.add_task(scrape_all_baselines)
    logger.info("Baseline Aggregator trigger received. Task enqueued.")
    
    return {"status": "ok", "message": "Baseline Aggregator started in background."}

@trigger_router.post("/trigger/security-master")
async def trigger_security_master(
    background_tasks: BackgroundTasks
):
    """Trigger the weekly security master refresh."""
    
    from app.scrapers.security_master import update_security_master
    
    background_tasks.add_task(update_security_master)
    logger.info("Security Master trigger received. Task enqueued.")
    
    return {"status": "ok", "message": "Security Master refresh started in background."}
