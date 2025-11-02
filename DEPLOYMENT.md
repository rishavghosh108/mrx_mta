# Production Deployment Checklist

## Pre-Deployment

### DNS Configuration
- [ ] Set up MX records pointing to your server
- [ ] Configure A/AAAA records for mail server hostname
- [ ] Set up reverse DNS (PTR) records with your hosting provider
- [ ] Publish SPF record for outbound IPs
- [ ] Generate DKIM keys and publish DNS records
- [ ] Publish DMARC policy record
- [ ] Verify DNS propagation (use `dig` or online tools)

### TLS Certificates
- [ ] Obtain valid TLS certificate (Let's Encrypt recommended)
- [ ] Set certificate auto-renewal (certbot cron job)
- [ ] Test certificate validity and chain
- [ ] Update `config.py` with certificate paths
- [ ] Set proper file permissions (readable by MTA user)

### Server Configuration
- [ ] Dedicated server or VPS with static IP
- [ ] Minimum 2 CPU cores, 2GB RAM for light load
- [ ] Open ports 25, 587, 465 in firewall
- [ ] Configure iptables/firewall rules
- [ ] Set up monitoring (CPU, memory, disk, network)
- [ ] Configure log rotation
- [ ] Set up automated backups

### Security Hardening
- [ ] Create dedicated `mta` user (non-root)
- [ ] Change `MTA_ADMIN_TOKEN` to secure random value
- [ ] Review and adjust rate limits
- [ ] Enable fail2ban for SMTP abuse
- [ ] Configure SELinux/AppArmor policies
- [ ] Disable unnecessary services
- [ ] Keep system packages updated

### Email Authentication
- [ ] Generate DKIM private key
  ```bash
  openssl genrsa -out data/dkim/default.private 2048
  openssl rsa -in data/dkim/default.private -pubout -outform DER | base64
  ```
- [ ] Publish DKIM public key in DNS
- [ ] Test DKIM signing
- [ ] Configure SPF alignment
- [ ] Test DMARC compliance

## Deployment

### Installation
```bash
# 1. Create MTA user
sudo useradd -r -s /bin/false mta

# 2. Clone/copy application
sudo mkdir -p /opt/mta
sudo chown mta:mta /opt/mta
cd /opt/mta

# 3. Set up virtual environment
sudo -u mta python3 -m venv venv
sudo -u mta venv/bin/pip install -r requirements.txt

# 4. Set permissions
sudo chown -R mta:mta /opt/mta
sudo chmod 750 /opt/mta
sudo chmod 600 /opt/mta/config.py
```

### Configuration
```bash
# 1. Edit config.py or set environment variables
sudo -u mta nano /opt/mta/.env

# Required settings:
# MTA_HOSTNAME=mail.example.com
# MTA_DOMAIN=example.com
# MTA_ADMIN_TOKEN=<generate secure random token>
# MTA_TLS_CERT=/etc/letsencrypt/live/mail.example.com/fullchain.pem
# MTA_TLS_KEY=/etc/letsencrypt/live/mail.example.com/privkey.pem

# 2. Load environment in service file
```

### Systemd Service
```bash
# Create service file
sudo nano /etc/systemd/system/mta.service
```

```ini
[Unit]
Description=RFC 5321 Compliant MTA
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=mta
Group=mta
WorkingDirectory=/opt/mta
EnvironmentFile=/opt/mta/.env
ExecStart=/opt/mta/venv/bin/python /opt/mta/app.py
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=mta

# Security
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/mta/data /opt/mta/logs

# Capabilities (for binding to port 25)
AmbientCapabilities=CAP_NET_BIND_SERVICE

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable mta
sudo systemctl start mta
sudo systemctl status mta
```

### Firewall Configuration
```bash
# UFW
sudo ufw allow 25/tcp    # SMTP
sudo ufw allow 587/tcp   # Submission
sudo ufw allow 465/tcp   # SMTPS (optional)
sudo ufw reload

# iptables
sudo iptables -A INPUT -p tcp --dport 25 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 587 -j ACCEPT
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

## Post-Deployment Testing

### SMTP Connectivity
```bash
# Test SMTP relay port
telnet mail.example.com 25

# Test submission port
openssl s_client -starttls smtp -connect mail.example.com:587
```

### DNS Verification
```bash
# Check MX records
dig example.com MX

# Check SPF
dig example.com TXT | grep spf

# Check DKIM
dig default._domainkey.example.com TXT

# Check DMARC
dig _dmarc.example.com TXT

# Check reverse DNS
dig -x YOUR_IP_ADDRESS
```

### Send Test Messages
```bash
# Install swaks
sudo apt install swaks

# Test authenticated send
swaks --to test@gmail.com \
      --from postmaster@example.com \
      --server mail.example.com:587 \
      --tls \
      --auth-user user@example.com \
      --auth-password yourpassword \
      --header "Subject: Test from MTA" \
      --body "Test message"
```

### Check Deliverability
- [ ] Send to Gmail and check "Show Original" for headers
- [ ] Send to Outlook/Hotmail
- [ ] Send to Yahoo Mail
- [ ] Verify DKIM signature passes
- [ ] Verify SPF passes
- [ ] Verify DMARC alignment
- [ ] Check spam score (mail-tester.com)

## Monitoring Setup

### Prometheus + Grafana
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mta'
    static_configs:
      - targets: ['localhost:8080']
        labels:
          instance: 'mta-prod'
```

### Log Monitoring
```bash
# Watch logs in real-time
sudo journalctl -u mta -f

# Check for errors
sudo journalctl -u mta -p err -n 50

# Search for specific queue ID
sudo journalctl -u mta | grep QUEUE_ID
```

### Alerts to Configure
- Queue length > 1000 messages
- Delivery failure rate > 10%
- Authentication failure spike
- Disk usage > 80%
- TLS certificate expiring in < 7 days
- High bounce rate (> 5%)

## Maintenance Tasks

### Daily
- [ ] Check queue size: `curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/queue/stats`
- [ ] Review error logs
- [ ] Monitor delivery rates

### Weekly
- [ ] Review bounce messages
- [ ] Check disk usage
- [ ] Review authentication failures
- [ ] Update blacklists if needed

### Monthly
- [ ] Rotate DKIM keys
- [ ] Review and update user accounts
- [ ] Check TLS certificate expiration
- [ ] Review rate limits and adjust if needed
- [ ] Database maintenance (vacuum, backup)

### Quarterly
- [ ] Security audit
- [ ] Review and update dependencies
- [ ] Load testing
- [ ] Disaster recovery drill

## Backup Strategy

### What to Backup
- [ ] Queue database (`data/mta.db`)
- [ ] Queued message files (`data/queue/`)
- [ ] User database (`data/users.json`)
- [ ] DKIM private keys (`data/dkim/`)
- [ ] Configuration files
- [ ] Logs (for compliance)

### Backup Script
```bash
#!/bin/bash
# /opt/mta/backup.sh

BACKUP_DIR="/backup/mta"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Stop MTA briefly for consistent backup
systemctl stop mta

# Backup data
tar -czf $BACKUP_DIR/mta_data_$DATE.tar.gz /opt/mta/data

# Restart MTA
systemctl start mta

# Keep only last 30 days
find $BACKUP_DIR -name "mta_data_*.tar.gz" -mtime +30 -delete
```

### Cron Job
```bash
# Add to /etc/cron.d/mta-backup
0 2 * * * root /opt/mta/backup.sh
```

## Disaster Recovery

### Restore from Backup
```bash
# 1. Stop service
sudo systemctl stop mta

# 2. Restore data
cd /opt/mta
sudo tar -xzf /backup/mta/mta_data_YYYYMMDD_HHMMSS.tar.gz

# 3. Fix permissions
sudo chown -R mta:mta /opt/mta/data

# 4. Restart
sudo systemctl start mta
```

### Failover Procedure
1. Update DNS MX records to point to backup server
2. Wait for DNS propagation (TTL)
3. Sync queue from primary to backup
4. Start MTA on backup server
5. Monitor delivery

## Performance Tuning

### High Volume Settings
```bash
# Increase delivery workers
MTA_DELIVERY_WORKERS=50

# Adjust connection limits
MTA_MAX_CONNECTIONS_GLOBAL=5000
MTA_MAX_CONN_PER_DOMAIN=20

# Increase queue processing
MTA_DELIVERY_INTERVAL=1

# Optimize database
sqlite3 data/mta.db "VACUUM;"
sqlite3 data/mta.db "ANALYZE;"
```

### System Tuning
```bash
# Increase file descriptors
echo "mta soft nofile 65536" >> /etc/security/limits.conf
echo "mta hard nofile 65536" >> /etc/security/limits.conf

# TCP tuning for high connection rates
echo "net.ipv4.tcp_tw_reuse = 1" >> /etc/sysctl.conf
echo "net.core.somaxconn = 4096" >> /etc/sysctl.conf
sysctl -p
```

## Troubleshooting

### Queue Not Processing
```bash
# Check delivery workers
curl -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/queue/stats

# Manually trigger delivery (not in current API, add if needed)
# Check logs
sudo journalctl -u mta -n 100
```

### High Bounce Rate
1. Check DNS records (SPF, DKIM, DMARC)
2. Verify reverse DNS
3. Check IP reputation (mxtoolbox.com)
4. Review bounce messages for common errors
5. Reduce sending rate if warming up new IP

### TLS Errors
```bash
# Test TLS
openssl s_client -starttls smtp -connect mail.example.com:587

# Check certificate
openssl x509 -in /etc/letsencrypt/live/mail.example.com/cert.pem -text -noout

# Verify chain
openssl verify -CAfile /etc/letsencrypt/live/mail.example.com/chain.pem \
               /etc/letsencrypt/live/mail.example.com/cert.pem
```

## Compliance

### Data Retention
- Configure log retention policy (GDPR compliance)
- Implement data anonymization for old logs
- Document retention periods

### Abuse Handling
- Set up abuse@example.com forwarding
- Set up postmaster@example.com forwarding
- Document abuse response procedures
- Implement unsubscribe handling

## Upgrade Procedure

```bash
# 1. Backup
/opt/mta/backup.sh

# 2. Stop service
sudo systemctl stop mta

# 3. Update code
cd /opt/mta
sudo -u mta git pull  # or copy new files

# 4. Update dependencies
sudo -u mta venv/bin/pip install -r requirements.txt --upgrade

# 5. Run migrations (if any)
# sudo -u mta venv/bin/python migrate.py

# 6. Restart
sudo systemctl start mta

# 7. Verify
sudo systemctl status mta
curl http://localhost:8080/health
```

## Security Incident Response

### Compromised Credentials
1. Immediately disable affected user
2. Rotate all passwords
3. Check queue for spam
4. Review logs for unauthorized access
5. Notify affected parties

### Spam Outbreak
1. Identify source (user/IP)
2. Disable/blacklist immediately
3. Purge spam from queue
4. Contact destination admins
5. Review and strengthen policies

---

**Last Updated**: 2025-10-29
**Review Schedule**: Quarterly
