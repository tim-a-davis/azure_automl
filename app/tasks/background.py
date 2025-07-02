import asyncio

from ..services.automl import AzureAutoMLService


async def monitor_run(run_id: str) -> None:
    """Periodically check run metrics until completion."""
    service = AzureAutoMLService()
    while True:
        metrics = service.get_run_metrics(run_id)
        status = metrics.get("status") if isinstance(metrics, dict) else None
        if status in {"Completed", "Failed", "Canceled"}:
            break
        await asyncio.sleep(30)


async def profile_dataset(dataset_id: str) -> None:
    """Trigger dataset profiling by submitting a job."""
    service = AzureAutoMLService()
    service.client.data.import_data(name=dataset_id)
    await asyncio.sleep(1)


async def collect_endpoint_metrics() -> None:
    """Continuously collect endpoint metrics for monitoring."""
    service = AzureAutoMLService()
    while True:
        service.list_endpoints()
        await asyncio.sleep(60)
