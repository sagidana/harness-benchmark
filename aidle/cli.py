import asyncio
import logging
from pathlib import Path

import click

from aidle import server
from aidle import mcp_server
from aidle.client import MazeClient


@click.group()
def main():
    pass


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind.")
@click.option("--port", default=8765, show_default=True, help="Port to listen on.")
@click.option("--data-dir", default=None, type=click.Path(), help="Directory for user state files. Defaults to ~/.aidle/users/.")
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level.")
def serve(host, port, data_dir, log_level):
    """Start the WebSocket server."""
    logging.basicConfig(level=log_level.upper(),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    asyncio.run(server.run(host, port, data_dir=Path(data_dir) if data_dir else None))


@main.command()
@click.option("--host", default="127.0.0.1", show_default=True, help="Server host.")
@click.option("--port", default=8765, show_default=True, help="Server port.")
@click.option("--username", required=True, help="Username to authenticate with.")
@click.option("--seed", default=None, type=int, help="Maze seed (ignored on resume).")
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level.")
def play(host, port, username, seed, log_level):
    """Connect to the server and play the maze challenge."""
    logging.basicConfig(level=log_level.upper(),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    uri = f"ws://{host}:{port}"
    client = MazeClient(uri, seed=seed, username=username)
    asyncio.run(client.run())


@main.command()
@click.option("--server", "server_uri", default="ws://127.0.0.1:8765", show_default=True,
              help="aidle WebSocket server URI.")
@click.option("--username", required=True, help="Username to authenticate with.")
@click.option("--log-level", default="WARNING", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False),
              help="Logging level (stderr).")
def mcp(server_uri, username, log_level):
    """Start an MCP server (stdio) that exposes aidle tools to an LLM."""
    logging.basicConfig(level=log_level.upper(),
                        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    mcp_server.run(server_uri, username=username)
