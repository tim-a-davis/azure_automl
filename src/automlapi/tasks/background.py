import asyncio

from datetime import datetime

from ..services.automl import AzureAutoMLService
from ..db import db_manager
from ..db.models import Run as RunModel, Dataset as DatasetModel


async def monitor_run(run_id: str) -> None:
    """Periodically check run metrics until completion."""
    service = AzureAutoMLService()
    SessionLocal = db_manager.get_session_local()
    db = SessionLocal()
    try:
        while True:
            metrics = service.get_run_metrics(run_id)
            status = metrics.get("status") if isinstance(metrics, dict) else None
            record = db.get(RunModel, run_id)
            if record:
                record.metrics = metrics
                if status in {"Completed", "Failed", "Canceled"}:
                    record.completed_at = datetime.utcnow()
                    db.commit()
                    break
                db.commit()
            if status in {"Completed", "Failed", "Canceled"}:
                break
            await asyncio.sleep(30)
    finally:
        db.close()


async def profile_dataset(dataset_id: str) -> None:
    """Trigger dataset profiling by submitting a job."""
    service = AzureAutoMLService()
    service.client.data.import_data(name=dataset_id)
    SessionLocal = db_manager.get_session_local()
    db = SessionLocal()
    try:
        record = db.get(DatasetModel, dataset_id)
        if record:
            record.profile_path = f"/profiles/{dataset_id}"
            db.commit()
    finally:
        db.close()
    await asyncio.sleep(1)


async def collect_endpoint_metrics() -> None:
    """Continuously collect endpoint metrics for monitoring."""
    service = AzureAutoMLService()
    while True:
        service.list_endpoints()
        await asyncio.sleep(60)
