from __future__ import annotations

from agent.logger import configure_logging, get_logger
from agent.config import get_settings

logger = get_logger(__name__)


def main() -> None:
    configure_logging(service_name="agent")

    logger.info("agent starting")
    logger.info(
        "example structured field",
        extra={"trace_id": "example-trace", "duration_ms": 12},
    )
    logger.info("settings: %s", get_settings())


if __name__ == "__main__":
    main()
