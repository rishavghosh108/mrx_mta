# RFC 5321 Compliant Mail Transfer Agent (MTA)

A production-ready SMTP/ESMTP mail transfer agent built with Python using clean MVC architecture. Implements RFC 5321, 3207 (STARTTLS), 4954 (AUTH), and includes persistent queuing, async delivery, rate limiting, and comprehensive administration API.

## 🎯 Overview

Modern mail transfer agent with clean **MVC + Services + Repositories** architecture:

- **RFC 5321** - Full SMTP/ESMTP protocol with state machine
- **RFC 3207** - STARTTLS with TLS 1.2+ support  
- **RFC 4954** - SMTP AUTH (PLAIN/LOGIN mechanisms)
- **RFC 3463** - Enhanced status codes
- **Async Delivery** - Worker pool with MX resolution
- **Persistent Queue** - SQLite + filesystem storage with retry logic
- **Rate Limiting** - Token bucket per-IP/user/domain
- **REST API** - Full queue, user, and policy management
- **Prometheus Metrics** - Production monitoring ready

## ✨ Features

**Core SMTP** - RFC 5321 compliant protocol, STARTTLS (RFC 3207), SMTP AUTH (RFC 4954), relay & submission ports  
**Queue Management** - Persistent queue with retry logic, exponential backoff, per-recipient tracking, MX resolution  
**Security** - Rate limiting (token bucket), blacklisting, greylisting, authentication lockout, relay prevention  
**Administration** - REST API for queue/user/policy management, Prometheus metrics, health checks  
**Architecture** - Clean MVC with services & repositories, dependency injection, comprehensive test suite

## 📋 Requirements

- Python 3.8+
- Virtual environment recommended

## 🚀 Quick Start

### 1. Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Generate TLS Certificates (for testing)

```bash
# Create certs directory
mkdir -p certs

# Generate self-signed certificate
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/server.key \
  -out certs/server.crt \
  -days 365 \
  -subj "/CN=mail.example.com"
```

**For production**: Use Let's Encrypt or your organization's CA.

### 3. Configure

Edit environment variables or modify `config.py`:

```bash
export MTA_HOSTNAME="mail.example.com"
export MTA_DOMAIN="example.com"
export MTA_ADMIN_TOKEN="your-secure-token-here"
```

### 4. Run

```bash
python app.py
```

The MTA will start:
- SMTP Relay on port 25 (requires root/sudo on Linux)
- SMTP Submission on port 587
- Admin API on port 8080

For testing without root:
```bash
export MTA_PORT_RELAY=2525
export MTA_PORT_SUBMISSION=5870
python app.py
```

## 🏗️ Architecture

Clean **5-layer MVC** architecture:

```
Controllers (SMTP protocol, REST API, Delivery workers)
    ↓
Services (Auth, Queue, Policy, Delivery - business logic)
    ↓
Repositories (User, Queue, Policy - data access)
    ↓
Models (Message, User, Policy - domain entities)
    ↓
Views (SMTP, JSON, Metrics - response formatting)
```

**Project Structure:**
```
models/              # Domain entities
repositories/        # Data persistence layer
services/            # Business logic
controllers/         # Protocol handlers & API
views/              # Response formatting
app.py              # Dependency injection & startup
```

## 🔧 Configuration

Key configuration options in `config.py` or environment variables:

### SMTP Settings
```bash
MTA_HOSTNAME=mail.example.com
MTA_DOMAIN=example.com
MTA_PORT_RELAY=25
MTA_PORT_SUBMISSION=587
MTA_MAX_MESSAGE_SIZE=35000000  # 35MB
MTA_MAX_RECIPIENTS=100
```

### TLS/Security
```bash
MTA_TLS_CERT=/path/to/server.crt
MTA_TLS_KEY=/path/to/server.key
MTA_TLS_REQUIRED_SUBMISSION=True
MTA_AUTH_REQUIRED=True
```

### Rate Limiting
```bash
MTA_RATE_LIMIT_IP=100          # messages/hour per IP
MTA_RATE_LIMIT_USER=200        # messages/hour per user
MTA_RATE_LIMIT_DOMAIN=1000     # messages/hour per domain
```

### Queue & Retry
```bash
MTA_MAX_QUEUE_AGE=604800       # 7 days in seconds
MTA_DELIVERY_WORKERS=10        # concurrent delivery workers
```

### Anti-Abuse
```bash
MTA_SPF_ENABLED=True
MTA_DKIM_ENABLED=True
MTA_DMARC_ENABLED=True
MTA_RBL_ENABLED=False
MTA_GREYLIST_ENABLED=False
```

## 📖 Usage Examples

### Sending via SMTP

```bash
# Using swaks (SMTP test tool)
swaks --to recipient@example.com \
      --from sender@yourdomain.com \
      --server localhost:587 \
      --tls \
      --auth-user test@example.com \
      --auth-password testpassword \
      --header "Subject: Test Email" \
      --body "This is a test message"
```

### Using telnet (manual SMTP)

```bash
telnet localhost 587
EHLO client.example.com
STARTTLS
# (connection upgrades to TLS)
EHLO client.example.com
AUTH PLAIN
# (provide base64 encoded credentials)
MAIL FROM:<sender@example.com>
RCPT TO:<recipient@example.com>
DATA
Subject: Test

Test message body.
.
QUIT
```

### Admin API Examples

```bash
# Set admin token
export ADMIN_TOKEN="your-secure-token-here"

# Get queue statistics
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     http://localhost:8080/api/queue/stats

# List queued messages
curl -H "Authorization: Bearer $ADMIN_TOKEN" \
     http://localhost:8080/api/queue/messages?limit=10

# Add user
curl -X POST \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"username":"user@example.com","password":"secret123"}' \
     http://localhost:8080/api/auth/users

# Blacklist an IP
curl -X POST \
     -H "Authorization: Bearer $ADMIN_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"ip":"192.0.2.100"}' \
     http://localhost:8080/api/policy/blacklist/ip

# Get Prometheus metrics
curl http://localhost:8080/api/metrics
```

## 🧪 Testing

```bash
pip install pytest pytest-asyncio
pytest tests/test_mta.py -v
```

## 📊 Monitoring

### Metrics Endpoint

Prometheus-compatible metrics at `/api/metrics`:

```
mta_queue_messages{status="active"} 42
mta_queue_messages{status="deferred"} 5
mta_queue_messages{status="bounce"} 2
```

### Logs

- `logs/mta.log` - Main application log
- `logs/smtp.log` - Detailed SMTP protocol transactions

## 🔐 Security Checklist

Before production deployment:

- [ ] Generate proper TLS certificates (Let's Encrypt)
- [ ] Change `MTA_ADMIN_TOKEN` to secure random value
- [ ] Set up reverse DNS (PTR) records for outbound IPs
- [ ] Publish SPF records in DNS
- [ ] Generate and publish DKIM keys
- [ ] Publish DMARC policy
- [ ] Configure firewall rules (restrict port 25 to known IPs)
- [ ] Set up monitoring and alerting
- [ ] Configure backup for queue database
- [ ] Review and adjust rate limits
- [ ] Enable RBL checking
- [ ] Set up abuse@ and postmaster@ addresses
- [ ] Test deliverability to major providers (Gmail, Outlook)

## 📄 DNS Configuration

### Required DNS Records

```dns
; MX Record
example.com.    IN MX   10 mail.example.com.

; A Record for MX
mail.example.com.   IN A    203.0.113.10

; PTR (Reverse DNS) - set with your hosting provider
10.113.0.203.in-addr.arpa.  IN PTR  mail.example.com.

; SPF Record
example.com.    IN TXT  "v=spf1 ip4:203.0.113.10 -all"

; DKIM Record (after generating keys)
default._domainkey.example.com. IN TXT "v=DKIM1; k=rsa; p=MIGfMA0GCS..."

; DMARC Record
_dmarc.example.com. IN TXT "v=DMARC1; p=quarantine; rua=mailto:dmarc@example.com"
```

## 🛠️ Production Deployment

### Using systemd

```ini
[Unit]
Description=RFC 5321 MTA
After=network.target

[Service]
Type=simple
User=mta
Group=mta
WorkingDirectory=/opt/mta
Environment="PATH=/opt/mta/venv/bin"
ExecStart=/opt/mta/venv/bin/python /opt/mta/app.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable mta
sudo systemctl start mta
sudo systemctl status mta
```

### Capacity Planning

- **Light load** (< 1000 msgs/hour): 2 delivery workers, 1 CPU core
- **Medium load** (< 10,000 msgs/hour): 10 delivery workers, 2-4 CPU cores
- **Heavy load** (> 10,000 msgs/hour): 20+ workers, dedicated server

## 🐛 Troubleshooting

### Common Issues

**Port 25 requires root**
```bash
# Option 1: Run with sudo
sudo python app.py

# Option 2: Use setcap (Linux)
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3

# Option 3: Use different port for testing
export MTA_PORT_RELAY=2525
```

**TLS certificate errors**
- Ensure certificate CN matches hostname
- Check file permissions (readable by MTA user)
- Verify certificate hasn't expired

**Messages stuck in queue**
- Check DNS resolution: `dig example.com MX`
- Verify network connectivity to destination
- Review logs for delivery errors
- Check if remote server is blocking your IP

**Authentication failures**
- Ensure TLS is enabled before AUTH
- Verify credentials in `data/users.json`
- Check for IP lockout in logs

## 📚 Additional Resources

- [RFC 5321 - SMTP](https://tools.ietf.org/html/rfc5321)
- [RFC 6409 - Message Submission](https://tools.ietf.org/html/rfc6409)
- [RFC 3207 - STARTTLS](https://tools.ietf.org/html/rfc3207)
- [RFC 4954 - SMTP AUTH](https://tools.ietf.org/html/rfc4954)
- [SPF RFC 7208](https://tools.ietf.org/html/rfc7208)
- [DKIM RFC 6376](https://tools.ietf.org/html/rfc6376)
- [DMARC RFC 7489](https://tools.ietf.org/html/rfc7489)

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

## 📚 Documentation

- `ARCHITECTURE_MVC.md` - Complete architecture guide
- `QUICKSTART.md` - Quick start guide with API examples
- `API.md` - Full API reference
- `DEPLOYMENT.md` - Production deployment guide

---

**Version 2.0.0** - MVC Architecture | Built with Python 3.8+ | RFC 5321 Compliant
