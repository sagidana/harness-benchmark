import asyncio
import logging
from pathlib import Path

import websockets
from websockets import ServerConnection

from aidle.protocol import ProtocolHandler
from aidle.storage import UserStore

logger = logging.getLogger(__name__)


async def run(host: str, port: int, data_dir: Path | None = None) -> None:
    store = UserStore(data_dir)
    logger.info("Starting WebSocket server on %s:%d  (data: %s)", host, port, store._dir)

    async def handle_client(websocket: ServerConnection) -> None:
        handler = ProtocolHandler(websocket, store)
        await handler.run()

    async with websockets.serve(handle_client, host, port):
        await asyncio.get_running_loop().create_future()  # run forever
