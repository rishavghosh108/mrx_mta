#!/usr/bin/env python3
"""
SMTP Test Script - Test MTA functionality
Tests various SMTP scenarios and generates sample traffic
"""
import smtplib
import ssl
import base64
import socket
from email.message import EmailMessage
from email.utils import make_msgid, formatdate


def test_connect(host='localhost', port=587):
    """Test basic connectivity"""
    print(f"\n{'='*60}")
    print(f"Test 1: Basic Connectivity to {host}:{port}")
    print('='*60)
    
    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            code, msg = smtp.ehlo_or_helo_if_needed()
            print(f"✓ Connected successfully")
            print(f"  Server response: {code} {msg.decode()}")
            
            # Check extensions
            if smtp.esmtp_features:
                print(f"  ESMTP Extensions:")
                for ext, params in smtp.esmtp_features.items():
                    print(f"    - {ext}: {params}")
            
            return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_starttls(host='localhost', port=587):
    """Test STARTTLS"""
    print(f"\n{'='*60}")
    print(f"Test 2: STARTTLS Negotiation")
    print('='*60)
    
    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            
            if smtp.has_extn('STARTTLS'):
                print("✓ STARTTLS extension available")
                
                # Create permissive context for self-signed certs
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                
                smtp.starttls(context=context)
                smtp.ehlo()
                print("✓ TLS negotiation successful")
                
                # Check cipher
                cipher = smtp.sock.cipher()
                if cipher:
                    print(f"  Cipher: {cipher[0]}")
                    print(f"  Protocol: {cipher[1]}")
                
                return True
            else:
                print("✗ STARTTLS not available")
                return False
    except Exception as e:
        print(f"✗ STARTTLS failed: {e}")
        return False


def test_auth_plain(host='localhost', port=587, username='test@example.com', password='testpassword'):
    """Test SMTP AUTH PLAIN"""
    print(f"\n{'='*60}")
    print(f"Test 3: SMTP AUTH PLAIN")
    print('='*60)
    
    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            
            # STARTTLS first
            if smtp.has_extn('STARTTLS'):
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                smtp.starttls(context=context)
                smtp.ehlo()
            
            # Authenticate
            smtp.login(username, password)
            print(f"✓ Authentication successful for {username}")
            return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ Authentication failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_send_mail(host='localhost', port=587, username='test@example.com', 
                   password='testpassword', to_addr='recipient@example.com'):
    """Test sending a complete email"""
    print(f"\n{'='*60}")
    print(f"Test 4: Send Complete Email")
    print('='*60)
    
    try:
        # Create message
        msg = EmailMessage()
        msg['From'] = username
        msg['To'] = to_addr
        msg['Subject'] = 'Test Email from MTA Test Script'
        msg['Date'] = formatdate(localtime=True)
        msg['Message-ID'] = make_msgid(domain=username.split('@')[1])
        
        msg.set_content("""
This is a test email sent from the MTA test script.

If you receive this, the MTA is working correctly!

Test Details:
- Sent via SMTP AUTH
- TLS encrypted
- RFC 5322 compliant headers
        """)
        
        # Send
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.set_debuglevel(0)
            smtp.ehlo()
            
            if smtp.has_extn('STARTTLS'):
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                smtp.starttls(context=context)
                smtp.ehlo()
            
            smtp.login(username, password)
            smtp.send_message(msg)
            
        print(f"✓ Email sent successfully")
        print(f"  From: {username}")
        print(f"  To: {to_addr}")
        print(f"  Message-ID: {msg['Message-ID']}")
        return True
    
    except Exception as e:
        print(f"✗ Send failed: {e}")
        return False


def test_multiple_recipients(host='localhost', port=587, username='test@example.com',
                             password='testpassword'):
    """Test sending to multiple recipients"""
    print(f"\n{'='*60}")
    print(f"Test 5: Multiple Recipients")
    print('='*60)
    
    recipients = [
        'recipient1@example.com',
        'recipient2@example.com',
        'recipient3@example.com'
    ]
    
    try:
        msg = EmailMessage()
        msg['From'] = username
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = 'Test: Multiple Recipients'
        msg['Date'] = formatdate(localtime=True)
        msg.set_content('This is a test email to multiple recipients.')
        
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            
            if smtp.has_extn('STARTTLS'):
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                smtp.starttls(context=context)
                smtp.ehlo()
            
            smtp.login(username, password)
            smtp.send_message(msg, to_addrs=recipients)
        
        print(f"✓ Email sent to {len(recipients)} recipients")
        for rcpt in recipients:
            print(f"  - {rcpt}")
        return True
    
    except Exception as e:
        print(f"✗ Send failed: {e}")
        return False


def test_size_limit(host='localhost', port=587, username='test@example.com',
                    password='testpassword'):
    """Test SIZE extension"""
    print(f"\n{'='*60}")
    print(f"Test 6: SIZE Extension")
    print('='*60)
    
    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            
            if smtp.has_extn('SIZE'):
                size_limit = smtp.esmtp_features.get('size', '0')
                print(f"✓ SIZE extension available")
                print(f"  Maximum message size: {size_limit} bytes")
                
                if size_limit and size_limit.isdigit():
                    size_mb = int(size_limit) / (1024 * 1024)
                    print(f"  ({size_mb:.1f} MB)")
                
                return True
            else:
                print("✗ SIZE extension not available")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_pipelining(host='localhost', port=587):
    """Test PIPELINING extension"""
    print(f"\n{'='*60}")
    print(f"Test 7: PIPELINING Extension")
    print('='*60)
    
    try:
        with smtplib.SMTP(host, port, timeout=10) as smtp:
            smtp.ehlo()
            
            if smtp.has_extn('PIPELINING'):
                print("✓ PIPELINING extension available")
                print("  Allows multiple commands before receiving responses")
                return True
            else:
                print("✗ PIPELINING extension not available")
                return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_manual_smtp(host='localhost', port=587):
    """Test manual SMTP commands"""
    print(f"\n{'='*60}")
    print(f"Test 8: Manual SMTP Transaction")
    print('='*60)
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        sock.connect((host, port))
        
        # Read greeting
        response = sock.recv(1024).decode()
        print(f"S: {response.strip()}")
        
        # EHLO
        sock.send(b"EHLO testclient.local\r\n")
        response = sock.recv(1024).decode()
        print(f"C: EHLO testclient.local")
        print(f"S: {response.strip()}")
        
        # QUIT
        sock.send(b"QUIT\r\n")
        response = sock.recv(1024).decode()
        print(f"C: QUIT")
        print(f"S: {response.strip()}")
        
        sock.close()
        print("✓ Manual SMTP transaction successful")
        return True
    
    except Exception as e:
        print(f"✗ Manual transaction failed: {e}")
        return False


def run_all_tests(host='localhost', port=587, username='test@example.com',
                  password='testpassword', recipient='recipient@example.com'):
    """Run all tests"""
    print("\n" + "="*60)
    print("MTA SMTP Test Suite")
    print("="*60)
    print(f"Target: {host}:{port}")
    print(f"Auth: {username}")
    print("="*60)
    
    results = {}
    
    # Run tests
    results['connect'] = test_connect(host, port)
    results['starttls'] = test_starttls(host, port)
    results['auth'] = test_auth_plain(host, port, username, password)
    results['send'] = test_send_mail(host, port, username, password, recipient)
    results['multi_rcpt'] = test_multiple_recipients(host, port, username, password)
    results['size'] = test_size_limit(host, port, username, password)
    results['pipelining'] = test_pipelining(host, port)
    results['manual'] = test_manual_smtp(host, port)
    
    # Summary
    print(f"\n{'='*60}")
    print("Test Summary")
    print('='*60)
    
    passed = sum(1 for r in results.values() if r)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {test_name}")
    
    print('='*60)
    print(f"Results: {passed}/{total} tests passed")
    print('='*60)
    
    return passed == total


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Test MTA SMTP functionality')
    parser.add_argument('--host', default='localhost', help='SMTP server host')
    parser.add_argument('--port', type=int, default=587, help='SMTP server port')
    parser.add_argument('--user', default='test@example.com', help='Username for auth')
    parser.add_argument('--password', default='testpassword', help='Password for auth')
    parser.add_argument('--to', default='recipient@example.com', help='Test recipient')
    
    args = parser.parse_args()
    
    success = run_all_tests(
        host=args.host,
        port=args.port,
        username=args.user,
        password=args.password,
        recipient=args.to
    )
    
    exit(0 if success else 1)
