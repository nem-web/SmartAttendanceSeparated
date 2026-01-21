# ML Service Docker Guide

Complete guide for running the ML Service in Docker as a standalone container.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Build Options](#build-options)
- [Running the Service](#running-the-service)
- [Configuration](#configuration)
- [Health Checks](#health-checks)
- [Troubleshooting](#troubleshooting)
- [Advanced Usage](#advanced-usage)

## Prerequisites

- Docker installed (version 20.10 or higher)
- Docker Compose installed (version 2.0 or higher)
- At least 2GB of available RAM
- 1-2 CPU cores recommended

## Quick Start

### Option 1: Using Docker Compose (Recommended)

1. Navigate to the ml-service directory:
```bash
cd server/ml-service
```

2. Build and start the service:
```bash
docker-compose up --build
```

3. The service will be available at `http://localhost:8001`

4. To run in detached mode:
```bash
docker-compose up -d --build
```

5. To stop the service:
```bash
docker-compose down
```

### Option 2: Using Docker CLI

1. Navigate to the ml-service directory:
```bash
cd server/ml-service
```

2. Build the Docker image:
```bash
docker build -t ml-service:latest .
```

3. Run the container:
```bash
docker run -d \
  --name ml-service \
  -p 8001:8001 \
  -e LOG_LEVEL=info \
  -e HOST=0.0.0.0 \
  -e PORT=8001 \
  ml-service:latest
```

4. Stop the container:
```bash
docker stop ml-service
docker rm ml-service
```

## Build Options

### Standard Build
```bash
docker build -t ml-service:latest .
```

### Build with No Cache (for fresh build)
```bash
docker build --no-cache -t ml-service:latest .
```

### Build with Custom Tag
```bash
docker build -t ml-service:v1.0.0 .
```

## Running the Service

### Docker Compose (Standalone)

The `docker-compose.yml` file in the ml-service directory is configured to run the ML service standalone:

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down

# Restart the service
docker-compose restart
```

### Docker Run with All Options

```bash
docker run -d \
  --name ml-service \
  -p 8001:8001 \
  -e LOG_LEVEL=info \
  -e HOST=0.0.0.0 \
  -e PORT=8001 \
  -e ML_MODEL=hog \
  -e NUM_JITTERS=5 \
  -e MIN_FACE_AREA_RATIO=0.04 \
  --memory=2g \
  --cpus=2 \
  --restart=unless-stopped \
  ml-service:latest
```

### Running with Custom Port

```bash
# Run on port 8080 instead of 8001
docker run -d \
  --name ml-service \
  -p 8080:8001 \
  -e PORT=8001 \
  ml-service:latest
```

## Configuration

### Environment Variables

The following environment variables can be configured:

| Variable | Description | Default | Options |
|----------|-------------|---------|---------|
| `HOST` | Server host address | `0.0.0.0` | Any valid IP |
| `PORT` | Server port | `8001` | Any available port |
| `LOG_LEVEL` | Logging level | `info` | `debug`, `info`, `warning`, `error` |
| `ML_MODEL` | Face detection model | `hog` | `hog` (CPU), `cnn` (GPU) |
| `NUM_JITTERS` | Face encoding re-samplings | `5` | 1-10 (higher = more accurate, slower) |
| `MIN_FACE_AREA_RATIO` | Minimum face size ratio | `0.04` | 0.01-0.5 |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | Comma-separated URLs |

### Using Environment File

1. Create a `.env` file:
```bash
cp .env.example .env
```

2. Edit the `.env` file with your configuration:
```env
HOST=0.0.0.0
PORT=8001
LOG_LEVEL=info
ML_MODEL=hog
NUM_JITTERS=5
MIN_FACE_AREA_RATIO=0.04
```

3. Run with environment file:
```bash
docker run -d \
  --name ml-service \
  -p 8001:8001 \
  --env-file .env \
  ml-service:latest
```

Or with Docker Compose:
```bash
docker-compose --env-file .env up -d
```

## Health Checks

### Check Service Health

```bash
# Using curl
curl http://localhost:8001/health

# Expected response:
{
  "status": "healthy",
  "service": "ML Service",
  "version": "1.0.0",
  "models_loaded": true,
  "uptime_seconds": 3600
}
```

### Check Container Health

```bash
# Check health status
docker ps | grep ml-service

# View detailed health info
docker inspect ml-service | grep -A 10 Health
```

### Monitor Logs

```bash
# Follow logs in real-time
docker logs -f ml-service

# View last 100 lines
docker logs --tail 100 ml-service

# With Docker Compose
docker-compose logs -f
```

## Testing the Service

### Test Root Endpoint

```bash
curl http://localhost:8001/

# Expected response:
{
  "service": "ML Service",
  "version": "1.0.0",
  "status": "running"
}
```

### Test API Documentation

Open in browser:
- Swagger UI: http://localhost:8001/docs
- ReDoc: http://localhost:8001/redoc

### Test Face Encoding (with sample image)

```bash
# Prepare a base64 encoded image
IMAGE_BASE64=$(base64 -w 0 your-image.jpg)

# Test encoding endpoint
curl -X POST http://localhost:8001/api/ml/encode-face \
  -H "Content-Type: application/json" \
  -d "{\"image_base64\": \"$IMAGE_BASE64\"}"
```

## Troubleshooting

### Issue: Container fails to start

**Solution 1**: Check logs
```bash
docker logs ml-service
```

**Solution 2**: Verify port availability
```bash
# Check if port 8001 is already in use
netstat -tulpn | grep 8001

# Or use a different port
docker run -d -p 8002:8001 ml-service:latest
```

**Solution 3**: Increase memory allocation
```bash
docker run -d --memory=3g ml-service:latest
```

### Issue: Build fails with SSL certificate errors

**Solution**: The Dockerfile already includes trusted hosts flags. If issues persist:

```bash
# Build with build args
docker build \
  --build-arg PIP_TRUSTED_HOST="pypi.org pypi.python.org files.pythonhosted.org" \
  -t ml-service:latest .
```

### Issue: "No module found" errors

**Solution**: Rebuild the image without cache
```bash
docker build --no-cache -t ml-service:latest .
```

### Issue: Healthcheck failing

**Solution 1**: Increase start period
```yaml
healthcheck:
  start_period: 60s  # Give more time for startup
```

**Solution 2**: Test healthcheck manually
```bash
docker exec ml-service curl -f http://localhost:8001/health
```

### Issue: Slow performance

**Solution 1**: Use HOG model (already default)
```bash
docker run -d -e ML_MODEL=hog ml-service:latest
```

**Solution 2**: Reduce NUM_JITTERS
```bash
docker run -d -e NUM_JITTERS=1 ml-service:latest
```

**Solution 3**: Allocate more CPU
```bash
docker run -d --cpus=3 ml-service:latest
```

### Issue: Out of memory errors

**Solution**: Increase memory limit
```bash
docker run -d --memory=3g ml-service:latest
```

### Issue: Container exits immediately

**Solution**: Check logs and ensure all dependencies are installed
```bash
docker logs ml-service
docker run -it ml-service:latest /bin/bash
# Inside container:
python -c "import face_recognition; print('OK')"
```

## Advanced Usage

### Running Multiple Instances

```bash
# Run 3 instances on different ports
docker run -d --name ml-service-1 -p 8001:8001 ml-service:latest
docker run -d --name ml-service-2 -p 8002:8001 ml-service:latest
docker run -d --name ml-service-3 -p 8003:8001 ml-service:latest
```

### With Docker Compose Scaling

Modify `docker-compose.yml`:
```yaml
services:
  ml-service:
    # ... existing config
    deploy:
      replicas: 3
```

Then run:
```bash
docker-compose up --scale ml-service=3
```

### Using with Nginx Load Balancer

Create `nginx.conf`:
```nginx
upstream ml_backend {
    server ml-service-1:8001;
    server ml-service-2:8001;
    server ml-service-3:8001;
}

server {
    listen 80;
    
    location / {
        proxy_pass http://ml_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Production Deployment

```bash
# Build production image
docker build -t ml-service:production .

# Run with production settings
docker run -d \
  --name ml-service-prod \
  -p 8001:8001 \
  -e LOG_LEVEL=warning \
  -e ML_MODEL=hog \
  -e NUM_JITTERS=3 \
  --memory=2g \
  --cpus=2 \
  --restart=always \
  --health-cmd="curl -f http://localhost:8001/health || exit 1" \
  --health-interval=30s \
  --health-retries=3 \
  --health-start-period=40s \
  ml-service:production
```

### Connecting to Backend API

When running the backend API separately, configure it to connect to ml-service:

```bash
# Run ML service
docker run -d --name ml-service -p 8001:8001 ml-service:latest

# Run backend API with ML_SERVICE_URL
docker run -d \
  --name backend-api \
  -p 8000:8000 \
  -e ML_SERVICE_URL=http://host.docker.internal:8001 \
  backend-api:latest
```

Or use Docker network:
```bash
# Create network
docker network create smart-attendance-network

# Run ML service
docker run -d \
  --name ml-service \
  --network smart-attendance-network \
  ml-service:latest

# Run backend API
docker run -d \
  --name backend-api \
  --network smart-attendance-network \
  -p 8000:8000 \
  -e ML_SERVICE_URL=http://ml-service:8001 \
  backend-api:latest
```

### Resource Monitoring

```bash
# Monitor container stats
docker stats ml-service

# Export metrics
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

### Backup and Export

```bash
# Save image
docker save ml-service:latest | gzip > ml-service-latest.tar.gz

# Load image
gunzip -c ml-service-latest.tar.gz | docker load
```

## Best Practices

1. **Use Docker Compose** for easier management and configuration
2. **Set resource limits** to prevent overconsumption
3. **Enable healthchecks** to ensure service reliability
4. **Use restart policies** for automatic recovery
5. **Monitor logs** regularly for issues
6. **Keep images updated** for security patches
7. **Use specific tags** instead of `latest` in production
8. **Configure CORS** appropriately for your environment
9. **Use HOG model** for CPU-based deployments
10. **Scale horizontally** for high load scenarios

## Security Considerations

**IMPORTANT: This service has NO built-in authentication. It is designed to be accessed only by the backend API service.**

### Production Security Requirements

1. **Network Isolation**: 
   - Run in a private network (Docker network, VPC, etc.)
   - Never expose port 8001 directly to the public internet
   - Use Docker network for service-to-service communication

2. **Firewall Rules**: 
   - Restrict access to port 8001 to only the backend API service IP
   - Use iptables or cloud provider security groups
   ```bash
   # Example: Allow only backend API container
   iptables -A INPUT -p tcp --dport 8001 -s backend-api-ip -j ACCEPT
   iptables -A INPUT -p tcp --dport 8001 -j DROP
   ```

3. **Reverse Proxy Authentication**:
   - Use Nginx or Traefik with authentication in front of ml-service
   - Example Nginx configuration:
   ```nginx
   location /ml/ {
       auth_request /auth;
       proxy_pass http://ml-service:8001/;
   }
   ```

4. **Docker Network Isolation**:
   ```bash
   # Create isolated network
   docker network create --internal ml-network
   
   # Run ml-service on isolated network
   docker run -d --network ml-network ml-service:latest
   ```

5. **Resource Limits**: Always set memory and CPU limits to prevent DoS

6. **Read-only Filesystem**: Consider using `--read-only` flag for additional security

7. **Non-root User**: The container runs as root by default. For production, consider adding a non-root user:
   ```dockerfile
   RUN useradd -m -u 1000 mluser
   USER mluser
   ```

### Recommended Production Setup

```bash
# 1. Create secure network
docker network create --internal ml-secure-network

# 2. Run ml-service on secure network only
docker run -d \
  --name ml-service \
  --network ml-secure-network \
  --memory=2g \
  --cpus=2 \
  --restart=always \
  ml-service:latest

# 3. Run backend-api with access to ml-service
docker run -d \
  --name backend-api \
  --network ml-secure-network \
  -p 8000:8000 \
  -e ML_SERVICE_URL=http://ml-service:8001 \
  backend-api:latest
```

Only the backend-api is exposed to external traffic, ml-service remains internal.

## Support

For issues and questions:
- Check the troubleshooting section above
- View logs: `docker logs ml-service`
- Refer to the main README.md for general information
- Check API documentation at http://localhost:8001/docs

## Related Documentation

- [Main README](./README.md) - General ML service documentation
- [Server README](../README.md) - Server architecture
- [Backend API README](../backend-api/README.md) - Backend API integration
