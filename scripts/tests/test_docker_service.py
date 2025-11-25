import asyncio
import logging
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.infrastructure.deployment.docker_service import DockerDeploymentService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting DockerDeploymentService test...")

    # Set DOCKER_HOST to the working socket URL
    os.environ["DOCKER_HOST"] = "unix:///var/run/docker.sock"
    logger.info(f"Set DOCKER_HOST to {os.environ['DOCKER_HOST']}")

    try:
        service = DockerDeploymentService()
        logger.info("Service initialized.")

        # Initialize docker client by accessing the property
        docker_client = await service.docker
        logger.info(f"Internal Docker client URL: {docker_client.docker_host}")

        logger.info("Listing deployments (containers)...")
        deployments = await service.list_deployments()

        logger.info(f"Found {len(deployments)} deployments (containers).")
        for d in deployments[:5]:  # Show first 5
            logger.info(f"  - {d.id} ({d.status})")

        if not deployments:
            logger.info("No containers found. Is Docker running?")
        else:
            logger.info("Docker connection successful.")

    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        if "service" in locals():
            await service.close()


if __name__ == "__main__":
    asyncio.run(main())
