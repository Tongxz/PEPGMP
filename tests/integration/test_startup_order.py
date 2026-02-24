"""
Integration tests for lifespan startup/shutdown order and state consistency.

These tests focus on the ordering and dependency guarantees in the FastAPI
lifespan implementation, so refactors (especially splitting lifespan) can
be validated with confidence.
"""
from __future__ import annotations

import asyncio
import importlib
import os
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

    # Lifespan utility functions (now used by src.api.app.lifespan)
    async def startup_database(app):
        event_log.append("startup.database_service")
        from src.services.database_service import get_db_service
        from src.database.connection import init_database
        try:
            await get_db_service()
            await init_database()
            event_log.append("startup.database_init")
            return True
        except Exception:
            # Mirror lifespan behavior: db init failure should not abort startup
            event_log.append("startup.database_init")
            return False

    async def startup_video_stream_manager():
        event_log.append("startup.video_stream_manager")
        return True

    async def startup_detection(app):
        event_log.append("startup.detection_service")
        max_concurrency = 1
        app.state.detection_lock = threading.Lock()
        app.state.detection_semaphore = asyncio.Semaphore(max_concurrency)
        from src.services import detection_service
        try:
            optimized, hairnet = detection_service.initialize_detection_services()
        except Exception:
            if os.getenv("ENVIRONMENT", "development") == "production":
                raise
            app.state.optimized_pipeline = None
            app.state.hairnet_pipeline = None
            app.state.detection_lock = None
            app.state.detection_semaphore = None
            return None, None
        app.state.optimized_pipeline = optimized
        app.state.hairnet_pipeline = hairnet
        return optimized, hairnet

    async def startup_regions(app):
        event_log.append("startup.region_service")
        return True

    async def startup_legacy_region_manager():
        event_log.append("startup.region_manager")
        return True

    async def startup_monitoring():
        event_log.append("startup.error_monitoring")
        event_log.append("startup.advanced_monitoring")
        return True

    async def startup_redis_listener():
        event_log.append("startup.redis_listener")
        return True

    async def startup_workflow_engine():
        event_log.append("startup.workflow_engine")
        return True

    async def shutdown_workflows():
        event_log.append("shutdown.workflow_engine")
        return True

    async def shutdown_redis_listener():
        event_log.append("shutdown.redis_listener")
        return True

    async def shutdown_video_stream_manager():
        event_log.append("shutdown.video_stream_manager")
        return True

    async def shutdown_database():
        event_log.append("shutdown.database_service")
        return True

    async def shutdown_monitoring():
        event_log.append("shutdown.error_monitoring")
        event_log.append("shutdown.advanced_monitoring")
        return True

    monkeypatch.setattr("src.api.lifespan_utils.startup_database", startup_database)
    monkeypatch.setattr(
        "src.api.lifespan_utils.startup_video_stream_manager",
        startup_video_stream_manager,
    )
    monkeypatch.setattr("src.api.lifespan_utils.startup_detection", startup_detection)
    monkeypatch.setattr("src.api.lifespan_utils.startup_regions", startup_regions)
    monkeypatch.setattr(
        "src.api.lifespan_utils.startup_legacy_region_manager",
        startup_legacy_region_manager,
    )
    monkeypatch.setattr("src.api.lifespan_utils.startup_monitoring", startup_monitoring)
    monkeypatch.setattr(
        "src.api.lifespan_utils.startup_redis_listener", startup_redis_listener
    )
    monkeypatch.setattr(
        "src.api.lifespan_utils.startup_workflow_engine", startup_workflow_engine
    )
    monkeypatch.setattr("src.api.lifespan_utils.shutdown_workflows", shutdown_workflows)
    monkeypatch.setattr(
        "src.api.lifespan_utils.shutdown_redis_listener", shutdown_redis_listener
    )
    monkeypatch.setattr(
        "src.api.lifespan_utils.shutdown_video_stream_manager",
        shutdown_video_stream_manager,
    )
    monkeypatch.setattr("src.api.lifespan_utils.shutdown_database", shutdown_database)
    monkeypatch.setattr("src.api.lifespan_utils.shutdown_monitoring", shutdown_monitoring)

    # Patch already-imported references in src.api.app
    monkeypatch.setattr(app_module, "startup_database", startup_database)
    monkeypatch.setattr(
        app_module, "startup_video_stream_manager", startup_video_stream_manager
    )
    monkeypatch.setattr(app_module, "startup_detection", startup_detection)
    monkeypatch.setattr(app_module, "startup_regions", startup_regions)
    monkeypatch.setattr(
        app_module, "startup_legacy_region_manager", startup_legacy_region_manager
    )
    monkeypatch.setattr(app_module, "startup_monitoring", startup_monitoring)
    monkeypatch.setattr(app_module, "startup_redis_listener", startup_redis_listener)
    monkeypatch.setattr(app_module, "startup_workflow_engine", startup_workflow_engine)
    monkeypatch.setattr(app_module, "shutdown_workflows", shutdown_workflows)
    monkeypatch.setattr(app_module, "shutdown_redis_listener", shutdown_redis_listener)
    monkeypatch.setattr(
        app_module, "shutdown_video_stream_manager", shutdown_video_stream_manager
    )
    monkeypatch.setattr(app_module, "shutdown_database", shutdown_database)
    monkeypatch.setattr(app_module, "shutdown_monitoring", shutdown_monitoring)

    # Database service (used by startup_database)
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

    # Detection services
    def initialize_detection_services():
        return optimized_pipeline, hairnet_pipeline

    monkeypatch.setattr(
        app_module.detection_service,
        "initialize_detection_services",
        initialize_detection_services,
    )

    return SimpleNamespace(
        optimized_pipeline=optimized_pipeline,
        hairnet_pipeline=hairnet_pipeline,
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
    
    Shutdown follows LIFO (Last In First Out) principle, which is the reverse of
    startup order. Services are shut down in the reverse order they were started.
    
    Startup order (partial): redis_listener (7) → workflow_engine (8)
    Expected shutdown order (LIFO): workflow_engine → redis_listener
    """
    monkeypatch.setenv("HBD_REGIONS_FILE", "/tmp/regions-not-exist.json")
    app = FastAPI()

    async with app_module.lifespan(app):
        pass

    def idx(name: str) -> int:
        return event_log.index(name)

    # Workflow engine (last started) should be shut down before Redis listener
    assert idx("shutdown.workflow_engine") < idx("shutdown.redis_listener")
    # Redis listener should be shut down before database
    assert idx("shutdown.redis_listener") < idx("shutdown.database_service")
