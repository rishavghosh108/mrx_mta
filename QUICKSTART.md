# MVC Architecture - Quick Start Guide

## 🚀 Running the MTA

```bash
cd /Users/apple/Desktop/mta
python3 app.py
```

You should see:
```
╔═══════════════════════════════════════════════════════════════╗
║   RFC 5321 Compliant Mail Transfer Agent (MTA)               ║
║   Version 2.0.0 - MVC Architecture                           ║
║   Architecture: MVC (Model-View-Controller)                  ║
╚═══════════════════════════════════════════════════════════════╝

2025-10-31 12:00:00 - Initializing repositories...
2025-10-31 12:00:00 - Initializing services...
2025-10-31 12:00:00 - Initializing controllers...
2025-10-31 12:00:00 - Starting 3 delivery workers...
2025-10-31 12:00:00 - SMTP Relay server started on 0.0.0.0:2525
2025-10-31 12:00:00 - SMTP Submission server started on 0.0.0.0:2587
2025-10-31 12:00:00 - Admin API: http://localhost:8025
2025-10-31 12:00:00 - MTA is ready and accepting connections
```

## 📡 Admin API Examples

### Health Check
```bash
curl http://localhost:8025/health
```

### Queue Statistics (requires auth)
```bash
curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/queue/stats
```

### List Queue Messages
```bash
curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/queue/messages?status=active&limit=10
```

### Get Message Details
```bash
curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/queue/message/MESSAGE_ID
```

### Requeue Message
```bash
curl -X POST \
     -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/queue/message/MESSAGE_ID/requeue
```

### Delete Message
```bash
curl -X DELETE \
     -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/queue/message/MESSAGE_ID
```

### List Users
```bash
curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/users
```

### Create User
```bash
curl -X POST \
     -H "Authorization: Bearer your-admin-token" \
     -H "Content-Type: application/json" \
     -d '{"username":"user@example.com","password":"secret123","rate_limit":100}' \
     http://localhost:8025/api/users
```

### Change Password
```bash
curl -X PUT \
     -H "Authorization: Bearer your-admin-token" \
     -H "Content-Type: application/json" \
     -d '{"password":"newsecret456"}' \
     http://localhost:8025/api/users/user@example.com/password
```

### Get Blacklist
```bash
curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/policy/blacklist
```

### Add to Blacklist
```bash
curl -X POST \
     -H "Authorization: Bearer your-admin-token" \
     -H "Content-Type: application/json" \
     -d '{"target":"spam.example.com","reason":"Known spam domain"}' \
     http://localhost:8025/api/policy/blacklist
```

### Remove from Blacklist
```bash
curl -X DELETE \
     -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/policy/blacklist/spam.example.com
```

### Get Rate Limit Stats
```bash
curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/policy/rate-limits
```

### Get Configuration
```bash
curl -H "Authorization: Bearer your-admin-token" \
     http://localhost:8025/api/config
```

### Prometheus Metrics (no auth)
```bash
curl http://localhost:8025/api/metrics
```

## 📧 SMTP Testing

### Send via Relay Port (no auth required)
```bash
telnet localhost 2525
EHLO client.example.com
MAIL FROM:<sender@example.com>
RCPT TO:<recipient@example.com>
DATA
Subject: Test Message

This is a test message.
.
QUIT
```

### Send via Submission Port (auth required)
```bash
telnet localhost 2587
EHLO client.example.com
AUTH PLAIN
# Base64 encoded: \0username\0password
# Example: echo -ne '\000user@example.com\000password123' | base64
MAIL FROM:<sender@example.com>
RCPT TO:<recipient@example.com>
DATA
Subject: Authenticated Test

This is an authenticated test message.
.
QUIT
```

## 🧪 Running Tests

### Install test dependencies:
```bash
pip3 install pytest pytest-asyncio
```

### Run all tests:
```bash
python3 -m pytest tests/test_mta.py -v
```

### Run specific test class:
```bash
python3 -m pytest tests/test_mta.py::TestQueueService -v
```

### Run specific test:
```bash
python3 -m pytest tests/test_mta.py::TestQueueService::test_enqueue_message -v
```

## 🔍 Monitoring

### Check logs:
```bash
tail -f logs/mta.log
```

### Check SMTP logs:
```bash
tail -f logs/smtp.log
```

### View queue directory:
```bash
ls -la data/queue/active/
ls -la data/queue/deferred/
ls -la data/queue/bounce/
```

## 🛠️ Development

### Adding a new service:
1. Create service in `services/` directory
2. Inject dependencies (repositories) in constructor
3. Implement business logic methods
4. Update `app.py` to initialize and inject into controllers

### Adding a new controller:
1. Create controller in `controllers/` directory
2. Inject dependencies (services) in constructor
3. Implement request handling methods
4. Update `app.py` to initialize and start controller

### Adding a new view:
1. Create view in `views/` directory
2. Implement formatting methods as static/class methods
3. Use view in controllers for response formatting

## 📚 Architecture Reference

### Request Flow:
```
Client Request
    ↓
Controller (handle request, validate)
    ↓
Service (business logic)
    ↓
Repository (data access)
    ↓
Model (domain entity)
    ↓
Repository (save/retrieve)
    ↓
Service (process results)
    ↓
View (format response)
    ↓
Controller (send response)
    ↓
Client Response
```

### Layer Responsibilities:
- **Models**: Domain entities, validation, business rules
- **Repositories**: Data persistence, queries, storage abstraction
- **Services**: Business logic, workflows, orchestration
- **Controllers**: Request handling, protocol implementation
- **Views**: Response formatting, presentation logic

## 🎯 Key Files

- `app.py` - Application entry point with dependency injection
- `config.py` - Configuration settings
- `controllers/smtp_controller.py` - SMTP protocol handler
- `controllers/admin_controller.py` - REST API endpoints
- `controllers/delivery_controller.py` - Delivery workers
- `services/*.py` - Business logic services
- `repositories/*.py` - Data access layer
- `models/*.py` - Domain entities
- `views/*.py` - Response formatters

## ✅ Checklist for Deployment

- [ ] Set `ADMIN_API_TOKEN` in config.py
- [ ] Configure TLS certificates if using STARTTLS
- [ ] Set up DNS MX records
- [ ] Configure SPF/DKIM/DMARC
- [ ] Set appropriate rate limits
- [ ] Configure logging levels
- [ ] Set up monitoring (Prometheus scraping)
- [ ] Test queue processing
- [ ] Test delivery to real domains
- [ ] Configure firewall rules
- [ ] Set up log rotation
- [ ] Back up configuration files

## 🔒 Security Notes

1. **Admin API Token**: Change `ADMIN_API_TOKEN` in config.py
2. **TLS**: Configure certificates for STARTTLS
3. **Authentication**: Require AUTH on submission port
4. **Rate Limiting**: Adjust limits based on your needs
5. **Blacklisting**: Maintain IP/domain blacklists
6. **Firewall**: Restrict admin API to trusted IPs

## 📞 Support

For issues or questions:
1. Check logs in `logs/` directory
2. Review configuration in `config.py`
3. Test with provided examples
4. Check test results for any failures

---

**MTA Version**: 2.0.0 (MVC Architecture)
**Python**: 3.8+
**Status**: ✅ Production Ready
