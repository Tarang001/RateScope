import asyncio
import logging
import signal

from app.core.logging import setup_logging
from app.pipeline.kafka import consume_loop, stop_kafka

logger = logging.getLogger(__name__)


async def main() -> None:
    setup_logging()
    logger.info("worker_starting", extra={"request_id": "-"})
    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _stop():
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            pass

    task = asyncio.create_task(consume_loop())
    await stop.wait()
    await stop_kafka()
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    logger.info("worker_stopped", extra={"request_id": "-"})


if __name__ == "__main__":
    asyncio.run(main())
