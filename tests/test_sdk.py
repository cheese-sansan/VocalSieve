import asyncio
from pathlib import Path

from vocalsieve.domain import PipelineConfig
from vocalsieve.sdk import AsyncVocalSieveClient, VocalSieveClient


def test_sync_sdk_context_manager(tmp_path: Path):
    source = tmp_path / "source"
    source.mkdir()
    with VocalSieveClient(tmp_path / "state.db") as client:
        job = client.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
        assert client.get_job(job.id).id == job.id


def test_async_sdk_basic_flow(tmp_path: Path):
    async def run():
        source = tmp_path / "source"
        source.mkdir()
        async with AsyncVocalSieveClient(tmp_path / "state.db") as client:
            job = await client.create_job(PipelineConfig(str(source), str(tmp_path / "out")))
            jobs = await client.list_jobs()
            assert jobs[0].id == job.id
            assert await client.query_results(job.id) == []

    asyncio.run(run())
