# Admin API Reference

## Authentication

All admin API endpoints (except `/health` and `/api/metrics`) require authentication using a Bearer token.

```bash
Authorization: Bearer YOUR_ADMIN_TOKEN
```

Set your admin token in `.env`:
```bash
MTA_ADMIN_TOKEN=your-secure-random-token
```

## Endpoints

### Health & Status

#### GET /health
Health check endpoint (no authentication required).

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-29T12:00:00",
  "version": "1.0.0"
}
```

#### GET /api/config
Get current MTA configuration.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "hostname": "mail.example.com",
  "domain": "example.com",
  "smtp_ports": {
    "relay": 25,
    "submission": 587,
    "smtps": 465
  },
  "limits": {
    "max_message_size": 35000000,
    "max_recipients": 100,
    "rate_limit_per_ip": 100,
    "rate_limit_per_user": 200
  },
  "features": {
    "spf_enabled": true,
    "dkim_enabled": true,
    "dmarc_enabled": true,
    "rbl_enabled": false,
    "greylist_enabled": false
  }
}
```

### Queue Management

#### GET /api/queue/stats
Get queue statistics.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "active": 42,
  "deferred": 5,
  "bounce": 2,
  "delivered": 1234
}
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/queue/stats
```

#### GET /api/queue/messages
List queued messages.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Query Parameters:**
- `limit` (integer, default: 100) - Maximum number of messages to return
- `status` (string, default: 'active') - Filter by status

**Response:**
```json
{
  "messages": [
    {
      "queue_id": "abc123@example.com",
      "sender": "sender@example.com",
      "recipients": ["recipient@example.com"],
      "status": "active",
      "attempts": 2,
      "created_at": "2025-10-29T12:00:00",
      "next_retry_at": "2025-10-29T12:15:00",
      "last_error": "Connection timeout",
      "recipient_status": {
        "recipient@example.com": {
          "status": "pending",
          "attempts": 2,
          "last_error": "Connection timeout"
        }
      }
    }
  ],
  "count": 1
}
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     "http://localhost:8080/api/queue/messages?limit=10&status=active"
```

#### GET /api/queue/message/<queue_id>
Get details of a specific message (not yet implemented).

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** TBD

#### POST /api/queue/message/<queue_id>/requeue
Requeue a message for immediate delivery (not yet implemented).

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** TBD

#### DELETE /api/queue/message/<queue_id>/delete
Delete a message from the queue (not yet implemented).

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:** TBD

### Policy Management

#### GET /api/policy/blacklist/ip
Get IP blacklist.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "blacklisted_ips": [
    "192.0.2.100",
    "198.51.100.200"
  ]
}
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/policy/blacklist/ip
```

#### POST /api/policy/blacklist/ip
Add IP to blacklist.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "ip": "192.0.2.100"
}
```

**Response:**
```json
{
  "success": true,
  "ip": "192.0.2.100"
}
```

**Example:**
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ip":"192.0.2.100"}' \
     http://localhost:8080/api/policy/blacklist/ip
```

#### DELETE /api/policy/blacklist/ip
Remove IP from blacklist.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "ip": "192.0.2.100"
}
```

**Response:**
```json
{
  "success": true,
  "ip": "192.0.2.100"
}
```

**Example:**
```bash
curl -X DELETE \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ip":"192.0.2.100"}' \
     http://localhost:8080/api/policy/blacklist/ip
```

#### GET /api/policy/blacklist/domain
Get domain blacklist.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "blacklisted_domains": [
    "spam.example.com",
    "malicious.example.org"
  ]
}
```

#### POST /api/policy/blacklist/domain
Add domain to blacklist.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "domain": "spam.example.com"
}
```

**Response:**
```json
{
  "success": true,
  "domain": "spam.example.com"
}
```

**Example:**
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"domain":"spam.example.com"}' \
     http://localhost:8080/api/policy/blacklist/domain
```

#### DELETE /api/policy/blacklist/domain
Remove domain from blacklist.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "domain": "spam.example.com"
}
```

**Response:**
```json
{
  "success": true,
  "domain": "spam.example.com"
}
```

### User Management

#### GET /api/auth/users
List all users.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "users": [
    {
      "username": "user@example.com",
      "enabled": true,
      "rate_limit": 200,
      "admin": false,
      "created_at": 1730203200.0
    }
  ]
}
```

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/auth/users
```

#### POST /api/auth/users
Add a new user.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "username": "newuser@example.com",
  "password": "securepassword123",
  "rate_limit": 200,
  "admin": false
}
```

**Response:**
```json
{
  "success": true,
  "username": "newuser@example.com"
}
```

**Example:**
```bash
curl -X POST \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"username":"newuser@example.com","password":"secret123"}' \
     http://localhost:8080/api/auth/users
```

#### DELETE /api/auth/users/<username>
Delete a user.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
```

**Response:**
```json
{
  "success": true,
  "username": "user@example.com"
}
```

**Example:**
```bash
curl -X DELETE \
     -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8080/api/auth/users/olduser@example.com
```

#### PUT /api/auth/users/<username>/password
Change user password.

**Headers:**
```
Authorization: Bearer YOUR_TOKEN
Content-Type: application/json
```

**Request Body:**
```json
{
  "password": "newsecurepassword"
}
```

**Response:**
```json
{
  "success": true,
  "username": "user@example.com"
}
```

**Example:**
```bash
curl -X PUT \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"password":"newpassword123"}' \
     http://localhost:8080/api/auth/users/user@example.com/password
```

### Metrics

#### GET /api/metrics
Get Prometheus-compatible metrics (no authentication required).

**Response (text/plain):**
```
# HELP mta_queue_messages Number of messages in queue by status
# TYPE mta_queue_messages gauge
mta_queue_messages{status="active"} 42
mta_queue_messages{status="deferred"} 5
mta_queue_messages{status="bounce"} 2
mta_queue_messages{status="delivered"} 1234
```

**Example:**
```bash
curl http://localhost:8080/api/metrics
```

**Prometheus Configuration:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mta'
    static_configs:
      - targets: ['localhost:8080']
        labels:
          instance: 'mta-production'
    metrics_path: '/api/metrics'
    scrape_interval: 15s
```

## Error Responses

All endpoints return standard HTTP status codes:

- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Missing or invalid authentication
- `403 Forbidden` - Valid auth but insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource already exists
- `500 Internal Server Error` - Server error
- `501 Not Implemented` - Feature not yet implemented

**Error Response Format:**
```json
{
  "error": "Error message describing what went wrong"
}
```

## Rate Limits

API endpoints are not currently rate-limited, but it's recommended to:
- Cache responses where appropriate
- Avoid polling endpoints more than once per second
- Use the metrics endpoint for monitoring instead of frequent queue queries

## Examples with curl

### Complete Workflow

```bash
# Set variables
export ADMIN_TOKEN="your-token-here"
export MTA_URL="http://localhost:8080"

# 1. Check MTA health
curl $MTA_URL/health

# 2. Get queue statistics
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     $MTA_URL/api/queue/stats

# 3. Add a new user
curl -X POST \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"username":"sender@example.com","password":"password123"}' \
     $MTA_URL/api/auth/users

# 4. List all users
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     $MTA_URL/api/auth/users

# 5. Blacklist a spammer
curl -X POST \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ip":"203.0.113.100"}' \
     $MTA_URL/api/policy/blacklist/ip

# 6. Check metrics
curl $MTA_URL/api/metrics

# 7. View queued messages
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     "$MTA_URL/api/queue/messages?limit=10"
```

### Using with Python

```python
import requests

MTA_URL = "http://localhost:8080"
ADMIN_TOKEN = "your-token-here"

headers = {
    "Authorization": f"Bearer {ADMIN_TOKEN}",
    "Content-Type": "application/json"
}

# Get queue stats
response = requests.get(f"{MTA_URL}/api/queue/stats", headers=headers)
stats = response.json()
print(f"Active messages: {stats.get('active', 0)}")

# Add user
user_data = {
    "username": "newuser@example.com",
    "password": "secure123",
    "rate_limit": 100
}
response = requests.post(
    f"{MTA_URL}/api/auth/users",
    headers=headers,
    json=user_data
)
print(f"User created: {response.json()}")

# Get metrics
response = requests.get(f"{MTA_URL}/api/metrics")
print(response.text)
```

## Future API Endpoints (Planned)

- `POST /api/queue/flush` - Force immediate delivery attempt for all queued messages
- `GET /api/logs/search` - Search logs by queue ID, sender, recipient, etc.
- `GET /api/stats/delivery` - Delivery statistics (success rate, avg delivery time, etc.)
- `POST /api/policy/ratelimit` - Dynamically adjust rate limits
- `GET /api/dkim/keys` - List DKIM keys
- `POST /api/dkim/rotate` - Rotate DKIM keys
- `GET /api/health/detailed` - Detailed health check with component status

---

**API Version:** 1.0.0  
**Last Updated:** 2025-10-29
