# Anisette Provisioning Server

A production-ready microservice for device authentication and provisioning, implementing an architecture similar to Anisette.

## Features

- **Dual Endpoints**: Supports `/1` (v1 shared state) and `/3` (v3 per-client unique state).
- **Persistent Storage**: Automatic state management following XDG Base Directory standards.
- **Async Architecture**: Built on FastAPI and Uvicorn for high-performance async request handling.
- **Docker Ready**: Multi-stage Dockerfile and Docker Compose configuration.
- **TLS/HTTPS**: Built-in support for TLS certificate configuration.
- **Health Checks**: Standard health endpoint for orchestration and monitoring.

## Quick Start

### Using Docker Compose (Recommended)

1. Clone the repository:
   ```bash
   git clone https://github.com/chenbusi123/anisette-server.git
   cd anisette-server
   ```

2. Copy environment template:
   ```bash
   cp .env.example .env
   ```

3. Start the server:
   ```bash
   docker-compose up -d
   ```

### Manual Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the server:
   ```bash
   python app.py
   ```

## API Documentation

The server provides interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Endpoints

- `GET /health`: Server health status.
- `POST /1`: V1 provisioning (Shared device state).
- `POST /3`: V3 provisioning (Unique per-client state).

## Configuration

| Environment Variable | Description | Default |
|----------------------|-------------|---------|
| `ANISETTE_HOSTNAME` | Bind hostname | `0.0.0.0` |
| `ANISETTE_PORT` | Bind port | `8000` |
| `ANISETTE_LOG_LEVEL` | Logging level | `INFO` |
| `ANISETTE_TLS_ENABLED` | Enable HTTPS | `false` |
| `ANISETTE_TLS_CERT_PATH` | TLS cert path | `None` |
| `ANISETTE_TLS_KEY_PATH` | TLS key path | `None` |
| `ANISETTE_STORAGE_PATH` | Data directory | `~/.local/share/anisette` |

## License

MIT
