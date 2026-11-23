from __future__ import annotations

import logging

from app.core.config import settings
from worker.consumer import QueueConsumer, _install_shutdown_handlers

logger = logging.getLogger("film_review.worker")


def main() -> None:
    logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logger.info("Worker startup", extra={"queue_url": settings.event_queue_url})
    consumer = QueueConsumer(queue_url=settings.event_queue_url, settings=settings)
    _install_shutdown_handlers(consumer)
    consumer.ensure_dlq()
    try:
        consumer.run_forever()
    except KeyboardInterrupt:
        logger.info("Worker interrupted; shutting down cleanly")
    finally:
        consumer.shutdown()
        logger.info("Worker shutdown complete")


if __name__ == "__main__":
    main()
