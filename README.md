# aidle

A CLI tool that runs a WebSocket challenge/game server implementing the [WCGP v1.0 protocol](docs/PROTOCOL.md).

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

## Protocol

See [docs/PROTOCOL.md](docs/PROTOCOL.md) for the full WCGP v1.0 specification: message envelope, all message types, cost accounting model, challenge extensibility, and a worked maze example.

## License

MIT © Sagi Dana
