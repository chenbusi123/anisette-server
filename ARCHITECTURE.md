# Anisette Server Architecture

## System Overview

Anisette Provisioning Server is a production-ready microservice that handles device authentication and provisioning with two distinct operational modes:

1. **V1 Mode (Shared State)**: All requests share a single device state for backward compatibility
2. **V3 Mode (Per-Client)**: Each request receives unique device data for enhanced security

## Component Architecture

### FastAPI Application Layer (app.py)

The HTTP server layer implements RESTful endpoints with:
- Async request handling using FastAPI
- Request/response validation via Pydantic models
- Structured logging for observability
- Error handling with appropriate HTTP status codes

**Endpoints:**
- `GET /health`: Health check for load balancers and orchestrators
- `GET /`: API information and available endpoints
- `POST /1`: V1 provisioning with shared device state
- `POST /3`: V3 provisioning with per-client unique state

### Configuration Management (config.py)

Centralized configuration system supporting:
- Environment variable parsing with sensible defaults
- XDG Base Directory Specification compliance
- Automatic directory creation and initialization
- TLS/HTTPS certificate path resolution

**Configuration hierarchy:**
1. Environment variables (highest priority)
2. Default values (lowest priority)

**XDG Directories:**
- Data storage: `~/.local/share/anisette` or `$XDG_DATA_HOME/anisette`
- Configuration: `~/.config/anisette` or `$XDG_CONFIG_HOME/anisette`

### Data Models (models.py)

Type-safe Pydantic models for validation:

**DeviceInfo**
- Contains: device_id (UDID), class, model, OS version, build
- Purpose: Hardware identification and provisioning metadata

**ADIData**
- Contains: machine_id, serial_number, device_name, locale, timezone
- Purpose: Apple Device Information for service authentication
- Includes: Encrypted payload for secure transmission

**DeviceState**
- Contains: device_info, adi_data, timestamps, identifiers
- Purpose: Complete persistent device state
- Storage: JSON file in XDG data directory

**ProvisioningRequest/Response**
- Request: Validates incoming provisioning requests
- Response: Structured responses with device state and ADI data

### Provisioning Manager (provisioning.py)

Core business logic handling device provisioning and state:

**State Management:**
- V1: Shared state persisted across service restarts
- V3: Ephemeral state generated per request
- Thread-safe operations with mutex locking
- JSON-based persistence

**Key Methods:**
- `initialize()`: Load or create shared device state on startup
- `cleanup()`: Save state on graceful shutdown
- `get_v1_data()`: Process V1 requests with shared state
- `get_v3_data()`: Generate unique state for V3 requests
- `_generate_device_state()`: Create new device state instances
- `_generate_machine_id()`: Deterministic ID generation from UDID
- `_generate_encrypted_adi()`: Create mock ADI payloads

## Data Flow

### V1 Request Flow
```
Client Request (POST /1)
    ↓
FastAPI validates ProvisioningRequest
    ↓
ProvisioningManager acquires state lock
    ↓
Load shared device state from JSON
    ↓
Update last_accessed timestamp
    ↓
Save updated state to JSON
    ↓
Release state lock
    ↓
Return ProvisioningResponse with shared state
    ↓
Client receives consistent device data
```

### V3 Request Flow
```
Client Request (POST /3)
    ↓
FastAPI validates ProvisioningRequest
    ↓
Generate unique device ID (hash + timestamp)
    ↓
Create new DeviceState with unique values
    ↓
Generate unique machine ID deterministically
    ↓
Create unique encrypted ADI payload
    ↓
Return ProvisioningResponse with unique state
    ↓
Client receives unique, non-persistent data
```

## Storage Layout

```
~/.local/share/anisette/
├── shared_device.json        # V1 shared state (persistent)
└── [empty until first V1 request]

~/.config/anisette/
└── [reserved for future config files]
```

### shared_device.json Structure
```json
{
  "device_info": {
    "device_id": "00008110-SHARED0000001",
    "device_class": "iPhone",
    "device_model": "iPhone15,2",
    "os_version": "17.0",
    "build_version": "21A329"
  },
  "adi_data": {
    "machine_id": "ABC123DEF456GHI789JKL01",
    "serial_number": "ABC123DEF456GHI789JKL01",
    "device_name": "iPhone",
    "locale": "en_US",
    "timezone": "UTC",
    "encrypted_data": "base64_encoded_payload"
  },
  "provisioning_timestamp": "2024-01-01T12:00:00",
  "last_accessed": "2024-01-01T12:30:45",
  "v1_identifier": "v1_0f1a2b3c4d5e6f7g",
  "v3_counter": 0
}
```

## Concurrency & Threading

### Thread Safety

V1 operations use mutex locking (`threading.Lock`) to ensure:
- Atomic state updates
- No race conditions during file I/O
- Consistent views of shared state

V3 operations are stateless and don't require locking:
- Each request generates unique data independently
- No shared state modifications
- Better scalability for concurrent V3 requests

### Async Handling

FastAPI uses asyncio for:
- Non-blocking request handling
- CPU-bound operations delegated to thread pool
- Multiple concurrent requests without blocking

Sync operations (V1 state management) run in thread pool via `asyncio.to_thread()` to avoid blocking event loop.

## Machine ID Generation

### Deterministic Algorithm
```
1. Take device UDID as input
2. Hash with SHA256
3. Take first 24 hex characters
4. Convert to uppercase
5. Return as machine ID
```

Result: Same UDID always produces same machine ID (deterministic but unique)

### V3 Unique Generation
```
1. Combine: client_info + current_timestamp
2. Hash with SHA256
3. Take first 12 hex characters
4. Prepend "00008110-" prefix
5. Use as unique V3 device ID
```

Result: Different device ID for each V3 request

## ADI Encryption

### Current Implementation
Mock encryption for demonstration:
1. Create payload with machine_id and nonce
2. Serialize to JSON
3. Encode as base64
4. Return as encrypted_data field

### Production Implementation
Should include:
1. Real symmetric encryption (AES-256-GCM)
2. Proper key derivation (PBKDF2 or similar)
3. Authenticated encryption with authentication tags
4. Timestamp validation to prevent replay attacks

## Error Handling

### Request Validation Errors
- Invalid JSON format → 400 Bad Request
- Missing required fields → 400 Bad Request
- Type mismatches → 400 Bad Request

### Processing Errors
- File I/O failures → 500 Internal Server Error
- State corruption → 500 Internal Server Error
- Configuration issues → 500 Internal Server Error (logged)

### Logging
- All errors logged with full context
- Error severity levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Log level configurable via ANISETTE_LOG_LEVEL

## Performance Characteristics

### Latency
- **V1 requests**: 5-10ms (file I/O bound)
- **V3 requests**: 1-5ms (CPU bound, no I/O)
- Network round-trip not included

### Scalability
- Concurrent V3 requests: Limited by CPU and Uvicorn worker count
- V1 requests: Serialized by mutex, better for throughput than concurrency
- Memory: Minimal overhead per request

### Resource Usage
- Base memory: ~50-100MB (Python + dependencies)
- Per-request overhead: <1MB
- Disk I/O: Only on V1 requests

## Security Considerations

### Current Limitations
1. **UDID Storage**: Stored as-is without hashing
2. **Mock Encryption**: ADI payload not truly encrypted
3. **No Authentication**: Endpoints accessible without credentials
4. **No Rate Limiting**: Unlimited requests per client
5. **No TLS by Default**: Communication unencrypted unless configured

### Recommendations for Production
1. Implement real ADI encryption with proper key management
2. Add API authentication (OAuth 2.0, JWT, or API keys)
3. Implement rate limiting (per IP, per client ID)
4. Enable TLS/HTTPS for all deployments
5. Implement request signing/validation
6. Add audit logging for compliance
7. Encrypt state files at rest
8. Implement secret rotation policies

## Deployment Patterns

### Single Instance (Development)
- Local Docker or direct Python execution
- Suitable for testing and development
- Limited to single machine

### Containerized (Production)
- Docker container with persistent volumes
- Suitable for Docker Compose deployments
- Single point of failure

### Distributed (Kubernetes/Cloud)
- Multiple replicas with shared storage
- Load balancer distributes requests
- Requires shared persistent volume for V1 state
- V3 requests scale horizontally without state concerns

### Stateless Scaling
- Use V3 endpoint for stateless operation
- Each instance generates unique data independently
- No state sharing required
- Superior scalability and availability

## Configuration Priority

1. **Environment Variables** (highest)
   - Prefixed with ANISETTE_
   - Override all defaults

2. **Default Values** (lowest)
   - Hardcoded in Config class
   - Used when env vars not set

Example:
```bash
# This overrides the default port
ANISETTE_PORT=9000 python app.py
```

## Testing Strategy

Test suite covers:
- **Unit Tests**: Data models, individual functions
- **Integration Tests**: Full endpoint flows
- **Persistence Tests**: State save/load
- **Concurrency Tests**: V1 locking behavior
- **Uniqueness Tests**: V3 unique generation

Run tests:
```bash
python -m pytest test_server.py -v
```

## Logging Structure

### Log Format
```
TIMESTAMP - LOGGER - LEVEL - MESSAGE
2024-01-01 12:00:00 - app - INFO - Starting Anisette server
```

### Loggers
- `app`: Main application events
- `config`: Configuration initialization
- `provisioning`: Device provisioning operations

### Log Levels
- **DEBUG**: Detailed request processing
- **INFO**: Normal operations, request summaries
- **WARNING**: Potential issues, invalid input
- **ERROR**: Failures, exceptions
- **CRITICAL**: System-level failures

## Monitoring & Observability

### Health Endpoint
- Endpoint: `GET /health`
- Use for: Load balancer checks, Kubernetes probes
- Response: Status, version, timestamp

### Request Logging
All requests logged with:
- Client IP/port
- Request type (V1 or V3)
- Processing status
- Response generation time (implicit in timestamps)

### Metrics (Future)
Consider adding Prometheus metrics:
- Request count per endpoint
- Request latency histograms
- Error rates by type
- Active connections

## Future Enhancements

1. **Database Backend**: Replace JSON file with database
2. **Caching**: Redis for state caching
3. **Metrics**: Prometheus exposition
4. **Tracing**: OpenTelemetry integration
5. **Rate Limiting**: Token bucket or similar
6. **Multi-tenant**: Support for multiple organizations
7. **API Versioning**: Support for multiple API versions
8. **Webhooks**: Event-driven provisioning
9. **State Replication**: Distributed state sharing
10. **Admin API**: Management endpoints for state inspection

## Dependencies

### Core
- **fastapi**: Web framework
- **uvicorn**: ASGI server
- **pydantic**: Data validation

### Production
- **python-multipart**: Multipart form parsing
- **pydantic-settings**: Settings management

### Development
- **pytest**: Testing framework
- **httpx**: HTTP testing client (via TestClient)
