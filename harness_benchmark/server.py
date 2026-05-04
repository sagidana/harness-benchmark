import asyncio
import logging
from pathlib import Path

import websockets
from websockets.asyncio.server import ServerConnection, serve

from harness_benchmark.protocol import ProtocolHandler
from harness_benchmark.storage import UserStore

logger = logging.getLogger(__name__)


async def run(host: str, port: int, data_dir: Path | None = None) -> None:
    store = UserStore(data_dir)
    logger.info("Starting WebSocket server on %s:%d  (data: %s)", host, port, store._dir)

    async def handle_client(websocket: ServerConnection) -> None:
        handler = ProtocolHandler(websocket, store)
        await handler.run()

    async with serve(handle_client, host, port):
        await asyncio.get_running_loop().create_future()  # run forever
