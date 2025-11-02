#!/usr/bin/env python3
"""
Pre-flight check - Verify MTA is ready to deploy
"""
import sys
import os
from pathlib import Path

def check(name, condition, fix_hint=None):
    """Check a condition and report"""
    status = "✓" if condition else "✗"
    color = "\033[92m" if condition else "\033[91m"
    reset = "\033[0m"
    print(f"{color}{status}{reset} {name}")
    if not condition and fix_hint:
        print(f"  → {fix_hint}")
    return condition

def main():
    print("="*60)
    print("MTA Pre-flight Checklist")
    print("="*60)
    print()
    
    all_ok = True
    
    # Check Python version
    py_version = sys.version_info
    all_ok &= check(
        f"Python version {py_version.major}.{py_version.minor}.{py_version.micro}",
        py_version >= (3, 8),
        "Upgrade to Python 3.8 or higher"
    )
    
    # Check virtual environment
    all_ok &= check(
        "Virtual environment exists",
        Path("venv").exists(),
        "Run: python3 -m venv venv"
    )
    
    # Check dependencies
    try:
        import flask
        import dns.resolver
        all_ok &= check("Dependencies installed", True)
    except ImportError as e:
        all_ok &= check("Dependencies installed", False, f"Run: pip install -r requirements.txt")
    
    # Check configuration files
    all_ok &= check(
        "Configuration file exists",
        Path("config.py").exists()
    )
    
    all_ok &= check(
        "Environment file exists",
        Path(".env").exists(),
        "Run: ./setup.sh"
    )
    
    # Check TLS certificates
    cert_exists = Path("certs/server.crt").exists()
    key_exists = Path("certs/server.key").exists()
    all_ok &= check(
        "TLS certificate exists",
        cert_exists and key_exists,
        "Run: ./setup.sh to generate self-signed cert"
    )
    
    # Check data directories
    all_ok &= check(
        "Data directories created",
        Path("data/queue/active").exists(),
        "Run: ./setup.sh"
    )
    
    # Check user database
    all_ok &= check(
        "User database exists",
        Path("data/users.json").exists(),
        "Run: ./setup.sh"
    )
    
    # Check modules can be imported
    try:
        sys.path.insert(0, str(Path.cwd()))
        import config
        import smtp_server
        import queue
        import auth
        import policy
        import delivery
        import admin
        all_ok &= check("All modules importable", True)
    except Exception as e:
        all_ok &= check("All modules importable", False, f"Error: {e}")
    
    # Check port availability (non-privileged ports for testing)
    import socket
    def port_available(port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('127.0.0.1', port))
            sock.close()
            return True
        except:
            return False
    
    all_ok &= check(
        "Port 2525 available (relay)",
        port_available(2525),
        "Another process is using port 2525"
    )
    
    all_ok &= check(
        "Port 5870 available (submission)",
        port_available(5870),
        "Another process is using port 5870"
    )
    
    all_ok &= check(
        "Port 8080 available (admin API)",
        port_available(8080),
        "Another process is using port 8080"
    )
    
    print()
    print("="*60)
    
    if all_ok:
        print("✓ All checks passed! MTA is ready to start.")
        print()
        print("To start the MTA:")
        print("  1. source venv/bin/activate")
        print("  2. export $(cat .env | xargs)")
        print("  3. python app.py")
        print()
        print("To test:")
        print("  python test_smtp.py")
        print()
        return 0
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        print()
        print("Quick fix: Run ./setup.sh")
        print()
        return 1

if __name__ == '__main__':
    sys.exit(main())
