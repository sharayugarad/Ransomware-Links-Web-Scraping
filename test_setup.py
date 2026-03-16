#!/usr/bin/env python3
"""
Test script to verify the setup and configuration.
"""
import json
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))


def test_imports():
    """Test if all required packages are installed."""
    print("Testing package imports...")
    try:
        import requests
        print("requests")
    except ImportError:
        print("requests - Run: pip install requests")
        return False
    
    try:
        from bs4 import BeautifulSoup
        print("beautifulsoup4")
    except ImportError:
        print("beautifulsoup4 - Run: pip install beautifulsoup4")
        return False
    
    try:
        import lxml
        print("lxml")
    except ImportError:
        print("lxml - Run: pip install lxml")
        return False
    
    return True


def test_config_file():
    """Test if config/email_config.json exists and has required variables."""
    print("\nTesting config/email_config.json...")
    config_path = Path("config/email_config.json")
    
    if not config_path.exists():
        print("config/email_config.json not found")
        print("   Create the config directory and add your email configuration")
        return False
    
    print("config/email_config.json exists")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print("JSON is valid")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return False
    
    required_fields = [
        'smtp_server',
        'smtp_port',
        'sender_email',
        'sender_password',
        'receiver_emails'
    ]
    
    missing = []
    for field in required_fields:
        value = config.get(field)
        if not value:
            missing.append(field)
            print(f"{field} - Missing or empty")
        elif field == 'sender_password' and len(str(value)) < 8:
            print(f"{field} - Seems too short (check if it's correct)")
        elif field == 'receiver_emails' and not isinstance(value, list):
            print(f"{field} - Must be an array/list")
            missing.append(field)
        elif field == 'receiver_emails' and len(value) == 0:
            print(f"{field} - Empty list, need at least one email")
            missing.append(field)
        else:
            if field == 'sender_password':
                print(f"{field} (length: {len(str(value))})")
            elif field == 'receiver_emails':
                print(f"{field} ({len(value)} recipient(s))")
            else:
                print(f"{field}")
    
    if missing:
        print(f"\n Please configure these fields in config/email_config.json: {', '.join(missing)}")
        return False
    
    # Check for placeholder values
    if '12345' in str(config.get('sender_password', '')):
        print("\n Warning: sender_password looks like a placeholder. Make sure to use your real password/app password.")
    
    return True


def test_modules():
    """Test if project modules can be imported."""
    print("\nTesting project modules...")
    try:
        from storage import URLStorage
        print("storage.py")
    except ImportError as e:
        print(f"storage.py - {e}")
        return False
    
    try:
        from scraper import URLScraper
        print("scraper.py")
    except ImportError as e:
        print(f"scraper.py - {e}")
        return False
    
    try:
        from email_sender import EmailSender
        print("email_sender.py")
    except ImportError as e:
        print(f"email_sender.py - {e}")
        return False
    
    try:
        from main import main
        print("main.py")
    except ImportError as e:
        print(f"main.py - {e}")
        return False
    
    return True


def test_directories():
    """Test if required directories exist."""
    print("\nTesting directory structure...")
    
    dirs = ['src', 'config', 'data', 'logs']
    for dir_name in dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"{dir_name}/")
        else:
            if dir_name in ['data', 'logs']:
                print(f"{dir_name}/ - Will be created automatically")
            else:
                print(f"{dir_name}/ - Missing! Please create this directory")
                return False
    
    return True


def test_email_connection():
    """Test SMTP connection (optional)."""
    print("\nTesting SMTP connection (optional)...")
    response = input("Do you want to test email connection? (y/n): ")
    
    if response.lower() != 'y':
        print("Skipped email connection test")
        return True
    
    try:
        import smtplib
        
        config_path = Path("config/email_config.json")
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        smtp_host = config.get('smtp_server')
        smtp_port = config.get('smtp_port', 587)
        smtp_user = config.get('sender_email')
        smtp_password = config.get('sender_password')
        use_ssl = config.get('use_ssl', False)
        
        print(f"Connecting to {smtp_host}:{smtp_port}...")
        
        if use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
            server.starttls()
        
        print("Authenticating...")
        server.login(smtp_user, smtp_password)
        server.quit()
        
        print("SMTP connection successful")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("SMTP authentication failed")
        print("   Check your sender_email and sender_password")
        print("   For Gmail, you need an App Password (not your regular password)")
        return False
    except Exception as e:
        print(f"SMTP connection failed: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Daily URL Scraper - Setup Test")
    print("=" * 60)
    
    results = []
    
    results.append(("Package Imports", test_imports()))
    results.append(("Configuration File", test_config_file()))
    results.append(("Project Modules", test_modules()))
    results.append(("Directory Structure", test_directories()))
    results.append(("SMTP Connection", test_email_connection()))
    
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name:.<40} {status}")
    
    print("=" * 60)
    
    if all(result[1] for result in results):
        print("\n All tests passed! You're ready to run the scraper.")
        print("\nRun the scraper with: python run.py")
    else:
        print("\n Some tests failed. Please fix the issues above.")
        print("\nRefer to README.md for setup instructions.")
    
    print()


if __name__ == "__main__":
    main()