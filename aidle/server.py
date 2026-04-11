import asyncio
import websockets
import logging

logger = logging.getLogger(__name__)


async def handle_client(websocket):
    logger.info("Client connected: %s", websocket.remote_address)
    try:
        async for message in websocket:
            pass  # server is empty for now
    except websockets.ConnectionClosed:
        pass
    finally:
        logger.info("Client disconnected: %s", websocket.remote_address)


async def run(host: str, port: int):
    logger.info("Starting WebSocket server on %s:%d", host, port)
    async with websockets.serve(handle_client, host, port):
        await asyncio.get_running_loop().create_future()  # run forever
