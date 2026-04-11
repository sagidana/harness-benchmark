# aidle

A CLI tool with a WebSocket server.

## Installation

```bash
pip install aidle
```

Or for development:

```bash
pip install -e .
```

## Usage

### `aidle serve`

Start the WebSocket server:

```bash
aidle serve
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Host to bind |
| `--port` | `8765` | Port to listen on |
| `--log-level` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`) |

Example:

```bash
aidle serve --host 127.0.0.1 --port 9000 --log-level DEBUG
```

## License

MIT © Sagi Dana
