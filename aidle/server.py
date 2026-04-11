import asyncio
import logging

import websockets
from websockets import ServerConnection

from aidle.protocol import ProtocolHandler

logger = logging.getLogger(__name__)


async def handle_client(websocket: ServerConnection) -> None:
    handler = ProtocolHandler(websocket)
    await handler.run()


async def run(host: str, port: int) -> None:
    logger.info("Starting WebSocket server on %s:%d", host, port)
    async with websockets.serve(handle_client, host, port):
        await asyncio.get_running_loop().create_future()  # run forever
