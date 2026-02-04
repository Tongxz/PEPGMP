"""
Integration tests for lifespan startup/shutdown order and state consistency.

These tests focus on the ordering and dependency guarantees in the FastAPI
lifespan implementation, so refactors (especially splitting lifespan) can
be validated with confidence.
"""
from __future__ import annotations

import asyncio
import importlib
import threading
from types import SimpleNamespace

import pytest
from fastapi import FastAPI


@pytest.fixture
def app_module():
    """Return the app module that defines the lifespan function."""
    return importlib.import_module("src.api.app")


@pytest.fixture
def event_log():
    """Collect ordered lifecycle events for assertion."""
    return []


@pytest.fixture
def patched_lifespan_dependencies(monkeypatch, app_module, event_log):
    """
    Patch heavyweight dependencies to fast, deterministic fakes while logging
    lifecycle order.
    """
    optimized_pipeline = object()
    hairnet_pipeline = object()

    # Module-level functions imported into src.api.app
    async def start_redis_listener():
        event_log.append("startup.redis_listener")

    async def shutdown_redis_listener():
        event_log.append("shutdown.redis_listener")

    def start_error_monitoring():
        event_log.append("startup.error_monitoring")

    def stop_error_monitoring():
        event_log.append("shutdown.error_monitoring")

    def start_monitoring():
        event_log.append("startup.advanced_monitoring")

    def stop_monitoring():
        event_log.append("shutdown.advanced_monitoring")

    monkeypatch.setattr(app_module, "start_redis_listener", start_redis_listener)
    monkeypatch.setattr(app_module, "shutdown_redis_listener", shutdown_redis_listener)
    monkeypatch.setattr(app_module, "start_error_monitoring", start_error_monitoring)
    monkeypatch.setattr(app_module, "stop_error_monitoring", stop_error_monitoring)
    monkeypatch.setattr(app_module, "start_monitoring", start_monitoring)
    monkeypatch.setattr(app_module, "stop_monitoring", stop_monitoring)

    # Database service
    class DummyDBService:
        pool = object()

    async def get_db_service():
        event_log.append("startup.database_service")
        return DummyDBService()

    async def init_database():
        event_log.append("startup.database_init")

    async def close_db_service():
        event_log.append("shutdown.database_service")

    monkeypatch.setattr("src.services.database_service.get_db_service", get_db_service)
    monkeypatch.setattr("src.database.connection.init_database", init_database)
    monkeypatch.setattr(
        "src.services.database_service.close_db_service", close_db_service
    )

    # Video stream manager
    async def init_stream_manager():
        event_log.append("startup.video_stream_manager")

    async def shutdown_stream_manager():
        event_log.append("shutdown.video_stream_manager")

    monkeypatch.setattr(
        "src.services.video_stream_manager.init_stream_manager", init_stream_manager
    )
    monkeypatch.setattr(
        "src.services.video_stream_manager.shutdown_stream_manager",
        shutdown_stream_manager,
    )

    # Detection services
    def initialize_detection_services():
        event_log.append("startup.detection_service")
        return optimized_pipeline, hairnet_pipeline

    monkeypatch.setattr(
        app_module.detection_service,
        "initialize_detection_services",
        initialize_detection_services,
    )

    # Region services
    class DummyRegionService:
        def __init__(self, repo):
            event_log.append("startup.region_service")

        async def get_all_regions(self, active_only=False):
            return []

        async def import_from_file(self, path):
            return {"imported": 0, "skipped": 0, "errors": 0}

    class DummyRegionRepo:
        def __init__(self, pool):
            self.pool = pool

    monkeypatch.setattr(
        "src.domain.services.region_service.RegionDomainService", DummyRegionService
    )
    monkeypatch.setattr(
        "src.infrastructure.repositories.postgresql_region_repository.PostgreSQLRegionRepository",
        DummyRegionRepo,
    )

    def initialize_region_service(_path):
        event_log.append("startup.region_manager")

    monkeypatch.setattr(
        "src.services.region_service.initialize_region_service",
        initialize_region_service,
    )

    # Workflow engine
    class DummyTask:
        def done(self):
            return True

        def cancel(self):
            return None

    class DummyWorkflowEngine:
        def __init__(self):
            self.running_workflows = {"wf-1": DummyTask()}
            self.cancel_events = {}

        async def recover_state(self):
            event_log.append("startup.workflow_engine")

        async def create_workflow(self, workflow_dict):
            event_log.append("startup.workflow_engine.load")
            return {"success": True}

        async def stop_workflow(self, workflow_id):
            event_log.append("shutdown.workflow_engine")
            self.running_workflows.pop(workflow_id, None)
            return {"success": True}

    dummy_engine = DummyWorkflowEngine()
    monkeypatch.setattr("src.workflow.workflow_engine.workflow_engine", dummy_engine)

    async def get_async_session():
        class DummySession:
            pass

        yield DummySession()

    monkeypatch.setattr("src.database.connection.get_async_session", get_async_session)

    class DummyWorkflow:
        def __init__(self):
            self.id = "wf-1"
            self.name = "demo"
            self.status = "active"
            self.trigger = "schedule"

        def to_dict(self):
            return {
                "id": self.id,
                "name": self.name,
                "status": self.status,
                "trigger": self.trigger,
            }

    async def get_all(_session):
        return [DummyWorkflow()]

    monkeypatch.setattr("src.database.dao.WorkflowDAO.get_all", get_all)

    return SimpleNamespace(
        optimized_pipeline=optimized_pipeline,
        hairnet_pipeline=hairnet_pipeline,
        workflow_engine=dummy_engine,
    )


@pytest.mark.asyncio
async def test_startup_order_dependencies(app_module, event_log, patched_lifespan_dependencies, monkeypatch):
    """
    Validate startup ordering between database, detection, redis listener,
    region service, and workflow engine initialization.
    """
    monkeypatch.setenv("HBD_REGIONS_FILE", "/tmp/regions-not-exist.json")
    app = FastAPI()

    async with app_module.lifespan(app):
        pass

    def idx(name: str) -> int:
        return event_log.index(name)

    assert idx("startup.database_init") < idx("startup.detection_service")
    assert idx("startup.detection_service") < idx("startup.redis_listener")
    assert idx("startup.database_service") < idx("startup.region_service")
    assert idx("startup.detection_service") < idx("startup.workflow_engine")


@pytest.mark.asyncio
async def test_state_consistency_after_detection_init(app_module, event_log, patched_lifespan_dependencies, monkeypatch):
    """
    Ensure detection-related state is available after detection service init.
    """
    monkeypatch.setenv("HBD_REGIONS_FILE", "/tmp/regions-not-exist.json")
    app = FastAPI()

    async with app_module.lifespan(app):
        assert app.state.optimized_pipeline is patched_lifespan_dependencies.optimized_pipeline
        assert app.state.hairnet_pipeline is patched_lifespan_dependencies.hairnet_pipeline
        assert app.state.detection_lock is not None
        assert isinstance(app.state.detection_lock, type(threading.Lock()))
        assert app.state.detection_semaphore is not None
        assert isinstance(app.state.detection_semaphore, asyncio.Semaphore)


@pytest.mark.asyncio
async def test_startup_continues_when_db_init_fails(app_module, event_log, patched_lifespan_dependencies, monkeypatch):
    """
    Simulate database init failure and confirm other services still start.
    """
    monkeypatch.setenv("HBD_REGIONS_FILE", "/tmp/regions-not-exist.json")

    async def failing_init_database():
        event_log.append("startup.database_init")
        raise RuntimeError("db init failed")

    monkeypatch.setattr("src.database.connection.init_database", failing_init_database)

    app = FastAPI()
    async with app_module.lifespan(app):
        pass

    assert "startup.detection_service" in event_log
    assert "startup.redis_listener" in event_log
    assert "startup.workflow_engine" in event_log


@pytest.mark.asyncio
async def test_startup_continues_when_detection_init_fails_non_production(app_module, event_log, patched_lifespan_dependencies, monkeypatch):
    """
    Simulate detection init failure in non-production and confirm app still starts.
    """
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("HBD_REGIONS_FILE", "/tmp/regions-not-exist.json")

    def failing_detection_init():
        event_log.append("startup.detection_service")
        raise RuntimeError("detection init failed")

    monkeypatch.setattr(
        app_module.detection_service,
        "initialize_detection_services",
        failing_detection_init,
    )

    app = FastAPI()
    async with app_module.lifespan(app):
        assert app.state.optimized_pipeline is None
        assert app.state.hairnet_pipeline is None
        assert app.state.detection_lock is None
        assert app.state.detection_semaphore is None

    assert "startup.redis_listener" in event_log


@pytest.mark.asyncio
async def test_detection_init_failure_blocks_startup_in_production(app_module, event_log, patched_lifespan_dependencies, monkeypatch):
    """
    In production, detection init failure should abort startup.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("HBD_REGIONS_FILE", "/tmp/regions-not-exist.json")

    def failing_detection_init():
        event_log.append("startup.detection_service")
        raise RuntimeError("detection init failed")

    monkeypatch.setattr(
        app_module.detection_service,
        "initialize_detection_services",
        failing_detection_init,
    )

    app = FastAPI()
    with pytest.raises(RuntimeError):
        async with app_module.lifespan(app):
            pass

    assert "startup.redis_listener" not in event_log


@pytest.mark.asyncio
async def test_shutdown_order_dependencies(app_module, event_log, patched_lifespan_dependencies, monkeypatch):
    """
    Validate shutdown ordering between redis listener, workflow engine, and DB service.
    """
    monkeypatch.setenv("HBD_REGIONS_FILE", "/tmp/regions-not-exist.json")
    app = FastAPI()

    async with app_module.lifespan(app):
        pass

    def idx(name: str) -> int:
        return event_log.index(name)

    assert idx("shutdown.redis_listener") < idx("shutdown.workflow_engine")
    assert idx("shutdown.workflow_engine") < idx("shutdown.database_service")
