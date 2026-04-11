import asyncio
import logging
import click
from aidle import server
from aidle.client import MazeClient


@click.group()
def main():
    pass


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind.")
@click.option("--port", default=8765, show_default=True, help="Port to listen on.")
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level.")
def serve(host, port, log_level):
    """Start the WebSocket server."""
    logging.basicConfig(level=log_level.upper(),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(server.run(host, port))


@main.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Server host.")
@click.option("--port", default=8765, show_default=True, help="Server port.")
@click.option("--seed", default=None, type=int, help="Maze seed for reproducibility.")
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level.")
def play(host, port, seed, log_level):
    """Connect to the server and play the maze challenge."""
    logging.basicConfig(level=log_level.upper(),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    uri = f"ws://{host}:{port}"
    client = MazeClient(uri, seed=seed)
    asyncio.run(client.run())
