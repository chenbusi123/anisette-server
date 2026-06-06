# Deployment Guide

This guide covers deploying Anisette Provisioning Server to various platforms.

## Docker Compose (Local/Development)

### Basic Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/chenbusi123/anisette-server.git
   cd anisette-server
   ```

2. Create `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Start server:
   ```bash
   docker-compose up -d
   ```

4. Verify health:
   ```bash
   curl http://localhost:8000/health
   ```

### With TLS/HTTPS

1. Generate self-signed certificates:
   ```bash
   mkdir -p certs
   openssl req -x509 -newkey rsa:4096 -nodes -out certs/cert.pem -keyout certs/key.pem -days 365
   ```

2. Update `.env`:
   ```
   ANISETTE_TLS_ENABLED=true
   ANISETTE_TLS_CERT_PATH=/app/certs/cert.pem
   ANISETTE_TLS_KEY_PATH=/app/certs/key.pem
   ```

3. Update `docker-compose.yml` to uncomment certs volume mount.

4. Restart service:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

## Kubernetes Deployment

### ConfigMap & Secrets Setup

Create `configmap.yaml`:
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: anisette-config
data:
  ANISETTE_HOSTNAME: "0.0.0.0"
  ANISETTE_PORT: "8000"
  ANISETTE_LOG_LEVEL: "INFO"
  ANISETTE_TLS_ENABLED: "false"
```

Create `secret.yaml` for TLS:
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: anisette-tls
type: Opaque
data:
  cert.pem: <base64-encoded-cert>
  key.pem: <base64-encoded-key>
```

### Deployment Manifest

Create `deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: anisette-server
spec:
  replicas: 3
  selector:
    matchLabels:
      app: anisette
  template:
    metadata:
      labels:
        app: anisette
    spec:
      containers:
      - name: server
        image: ghcr.io/chenbusi123/anisette-server:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: anisette-config
        volumeMounts:
        - name: data
          mountPath: /data
        - name: config
          mountPath: /config
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: data
        emptyDir: {}
      - name: config
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: anisette-service
spec:
  type: LoadBalancer
  selector:
    app: anisette
  ports:
  - port: 80
    targetPort: 8000
```

Deploy:
```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f deployment.yaml
```

## AWS ECS

### Task Definition

Create `task-definition.json`:
```json
{
  "family": "anisette-server",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "containerDefinitions": [
    {
      "name": "anisette",
      "image": "ghcr.io/chenbusi123/anisette-server:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "ANISETTE_HOSTNAME", "value": "0.0.0.0"},
        {"name": "ANISETTE_PORT", "value": "8000"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/anisette-server",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      }
    }
  ]
}
```

Register task:
```bash
aws ecs register-task-definition --cli-input-json file://task-definition.json
```

### ECS Service

Create service:
```bash
aws ecs create-service \
  --cluster default \
  --service-name anisette-server \
  --task-definition anisette-server \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

## Environment Variables Summary

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| ANISETTE_HOSTNAME | Bind address | No | 0.0.0.0 |
| ANISETTE_PORT | Bind port | No | 8000 |
| ANISETTE_TLS_ENABLED | Enable HTTPS | No | false |
| ANISETTE_TLS_CERT_PATH | TLS certificate | Yes if TLS enabled | N/A |
| ANISETTE_TLS_KEY_PATH | TLS private key | Yes if TLS enabled | N/A |
| ANISETTE_LOG_LEVEL | Log level | No | INFO |
| ANISETTE_STORAGE_PATH | Data storage path | No | ~/.local/share/anisette |
| ANISETTE_CONFIG_PATH | Config path | No | ~/.config/anisette |

## Persistent Storage

### Docker Compose

Update `docker-compose.yml` to use host paths:
```yaml
volumes:
  - /path/to/persistent/data:/data
  - /path/to/persistent/config:/config
```

### Kubernetes

Use PersistentVolume and PersistentVolumeClaim:
```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: anisette-data-pv
spec:
  capacity:
    storage: 10Gi
  accessModes:
    - ReadWriteOnce
  hostPath:
    path: "/data/anisette"
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: anisette-data-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

## Monitoring & Logging

### Health Check Endpoint

All platforms can monitor the `/health` endpoint:
```bash
curl -X GET http://localhost:8000/health
```

Response format:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T12:00:00"
}
```

### Logs

Server logs are sent to stdout/stderr by default. Configure log aggregation:
- Docker: Use `docker logs anisette-server`
- Kubernetes: Use `kubectl logs deployment/anisette-server`
- AWS ECS: Check CloudWatch logs at `/ecs/anisette-server`

## Troubleshooting

### Port Already in Use
```bash
lsof -i :8000
kill -9 <PID>
```

### TLS Certificate Errors
Verify certificate and key exist and are readable:
```bash
openssl x509 -in certs/cert.pem -text -noout
openssl pkey -in certs/key.pem -text -noout
```

### Storage Permission Issues
Ensure data directories are writable:
```bash
chmod 755 /data /config
ls -la /data
```

### Device State Corruption
Delete corrupted state file to regenerate:
```bash
rm /data/shared_device.json
```

Server will generate new shared device state on next startup.
