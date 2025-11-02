# Quick Migration Guide - Old to New

## Import Changes

### ❌ OLD (Don't use - files deleted/moved)
```python
# These imports will FAIL
from queue import QueueManager
from auth import AuthManager
from policy import PolicyManager
import smtp_server
import admin
import delivery
```

### ✅ NEW (Use these instead)
```python
# Models
from models.message import Message, QueuedMessage
from models.user import User
from models.policy import PolicyRule, RateLimit, GreylistEntry
from models.delivery_status import DeliveryStatus, RecipientStatus

# Repositories
from repositories.user_repository import UserRepository
from repositories.queue_repository import QueueRepository
from repositories.policy_repository import PolicyRepository

# Services
from services.auth_service import AuthService
from services.queue_service import QueueService
from services.policy_service import PolicyService

# Configuration (still the same)
import config
```

## Common Patterns

### Creating a User
```python
# OLD
auth_manager = AuthManager()
auth_manager.add_user("test@example.com", "password")

# NEW
user_repo = UserRepository("data/users.json")
auth_service = AuthService(user_repo)
user = await auth_service.create_user("test@example.com", "password")
```

### Authenticating
```python
# OLD
auth_manager = AuthManager()
success = await auth_manager.authenticate("user", "pass", "127.0.0.1")

# NEW
user_repo = UserRepository("data/users.json")
auth_service = AuthService(user_repo)
user = await auth_service.authenticate("user", "pass", "127.0.0.1")
# Returns User object if successful, None if failed
```

### Enqueuing a Message
```python
# OLD
queue_manager = QueueManager()
msg = await queue_manager.enqueue(sender, recipients, data, session_info)

# NEW
queue_repo = QueueRepository("mta.db")
queue_service = QueueService(queue_repo)
queued_msg = await queue_service.enqueue_message(
    sender=sender,
    recipients=recipients,
    message_data=data,
    session_info=session_info
)
```

### Checking Rate Limits
```python
# OLD
policy_manager = PolicyManager()
allowed = await policy_manager.rate_limiter.check_limit("127.0.0.1", limit_type="ip")

# NEW
policy_repo = PolicyRepository("data/policy")
policy_service = PolicyService(policy_repo)
allowed = await policy_service.check_ip_rate_limit("127.0.0.1")
```

### Checking Blacklist
```python
# OLD
policy_manager = PolicyManager()
is_blocked = await policy_manager.check_blacklist(ip="127.0.0.1")

# NEW
policy_repo = PolicyRepository("data/policy")
policy_service = PolicyService(policy_repo)
is_blocked = await policy_service.check_blacklist(ip="127.0.0.1")
```

## File Locations

| Old File | New Location | Purpose |
|----------|--------------|---------|
| `queue.py` | `models/message.py` + `repositories/queue_repository.py` + `services/queue_service.py` | Split into layers |
| `auth.py` | `models/user.py` + `repositories/user_repository.py` + `services/auth_service.py` | Split into layers |
| `policy.py` | `models/policy.py` + `repositories/policy_repository.py` + `services/policy_service.py` | Split into layers |
| `smtp_server.py` | `legacy_backup/smtp_server.py` → Will become `controllers/smtp_controller.py` | Needs refactoring |
| `admin.py` | `legacy_backup/admin.py` → Will become `controllers/admin_controller.py` | Needs refactoring |
| `delivery.py` | `legacy_backup/delivery.py` → Will become `controllers/delivery_controller.py` | Needs refactoring |
| `app.py` | `legacy_backup/app.py` → Will be rewritten | Needs refactoring |

## Dependency Injection Pattern

The new architecture uses dependency injection:

```python
# Initialize repositories (data layer)
user_repo = UserRepository(config.AUTH_USERS_FILE)
queue_repo = QueueRepository(config.DB_PATH)
policy_repo = PolicyRepository(config.DATA_DIR)

# Initialize services (business logic layer)
auth_service = AuthService(user_repo)
queue_service = QueueService(queue_repo)
policy_service = PolicyService(policy_repo)

# Initialize controllers (request handling layer) - TO BE CREATED
smtp_controller = SMTPController(auth_service, queue_service, policy_service)
admin_controller = AdminController(auth_service, queue_service, policy_service)
delivery_controller = DeliveryController(queue_service, policy_service)
```

## Testing Updates

Update your tests to use the new structure:

```python
# OLD
from queue import QueueManager

def test_queue():
    qm = QueueManager()
    # test...

# NEW
from repositories.queue_repository import QueueRepository
from services.queue_service import QueueService

async def test_queue():
    repo = QueueRepository(":memory:")
    service = QueueService(repo)
    # test...
```

## Quick Checklist

- [ ] Update all imports to use new MVC structure
- [ ] Replace direct manager usage with services
- [ ] Use dependency injection pattern
- [ ] Update tests to use new structure
- [ ] Reference `legacy_backup/` for implementation details
- [ ] Don't try to import deleted files (queue.py, auth.py, policy.py)

## Need Help?

- Check `ARCHITECTURE_MVC.md` for full architecture details
- Check `legacy_backup/` for old implementation reference
- Check `CLEANUP.md` for what was deleted/moved
- Check `MVC_STATUS.md` for current progress
