# Anisette Server API Reference

## Base URL
Default base URL: `http://localhost:8000`

## Endpoints

### 1. Health Check
Returns the current health status of the server.

- **URL**: `/health`
- **Method**: `GET`
- **Auth required**: No

#### Success Response
- **Code**: 200 OK
- **Content**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00"
}
```

---

### 2. V1 Provisioning
Shared device state provisioning. All requests to this endpoint share the same device identifier and ADI data.

- **URL**: `/1`
- **Method**: `POST`
- **Auth required**: No
- **Payload**: `ProvisioningRequest`

#### Request Example
```json
{
  "client_id": "com.example.app",
  "device_info": {
    "device_id": "00008110-001234567890AB",
    "device_class": "iPhone",
    "device_model": "iPhone15,2",
    "os_version": "17.0",
    "build_version": "21A329"
  }
}
```

#### Success Response
- **Code**: 200 OK
- **Content**:
```json
{
  "success": true,
  "device_state": {
    "device_info": { ... },
    "adi_data": { ... },
    "provisioning_timestamp": "...",
    "last_accessed": "...",
    "v1_identifier": "...",
    "v3_counter": 0
  },
  "adi_data": {
    "machine_id": "...",
    "serial_number": "...",
    "device_name": "...",
    "locale": "en_US",
    "timezone": "UTC",
    "encrypted_data": "..."
  },
  "timestamp": "...",
  "request_id": "..."
}
```

---

### 3. V3 Provisioning
Per-client unique provisioning. Each request generates unique device data for the specific client.

- **URL**: `/3`
- **Method**: `POST`
- **Auth required**: No
- **Payload**: `ProvisioningRequest`

#### Request Example
```json
{
  "client_id": "com.example.app",
  "device_info": {
    "device_id": "00008110-001234567890AB",
    "device_class": "iPhone",
    "device_model": "iPhone15,2",
    "os_version": "17.0",
    "build_version": "21A329"
  }
}
```

#### Success Response
- **Code**: 200 OK
- **Content**: Same structure as V1, but with unique data.

---

### 4. Root Info
Returns basic API information.

- **URL**: `/`
- **Method**: `GET`

#### Success Response
- **Code**: 200 OK
- **Content**:
```json
{
  "name": "Anisette Provisioning Server",
  "version": "1.0.0",
  "endpoints": {
    "health": "/health",
    "provisioning_v1": "/1 (POST)",
    "provisioning_v3": "/3 (POST)"
  }
}
```

## Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad Request (Invalid payload) |
| 404 | Not Found |
| 500 | Internal Server Error |

## Schemas

### DeviceInfo
- `device_id`: string (required)
- `device_class`: string (required)
- `device_model`: string (required)
- `os_version`: string (required)
- `build_version`: string (required)

### ADIData
- `machine_id`: string
- `serial_number`: string
- `device_name`: string
- `locale`: string (default: "en_US")
- `timezone`: string (default: "UTC")
- `encrypted_data`: string (Base64)
