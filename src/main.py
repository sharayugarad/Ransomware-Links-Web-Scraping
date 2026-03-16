"""
Main orchestration module for the daily URL scraper.
"""
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from storage import MultiSourceStorage
from scraper import URLScraper
from email_sender import EmailSender


def setup_logging(log_dir: str = "logs", log_file: str = "scraper.log") -> logging.Logger:
    """Set up logging configuration with single append-only log file."""
    # Create logs directory
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # Single log file that appends
    log_path = Path(log_dir) / log_file
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Append mode ('a') instead of write mode ('w')
            logging.FileHandler(log_path, mode='a', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging to: {log_path} (append mode)")
    
    return logger


def load_config(config_path: str = "config/email_config.json") -> Dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            email_config = json.load(f)
        
        config = {
            # Email settings from JSON
            'smtp_host': email_config.get('smtp_server'),
            'smtp_port': email_config.get('smtp_port', 587),
            'smtp_user': email_config.get('sender_email'),
            'smtp_password': email_config.get('sender_password'),
            'from_email': email_config.get('sender_email'),
            'to_emails': email_config.get('receiver_emails', []),
            'use_ssl': email_config.get('use_ssl', False),
            
            # Scraper settings
            'timeout': email_config.get('timeout', 30),
            'max_retries': email_config.get('max_retries', 3),
            'filter_date': email_config.get('filter_date', '2025-01-14'),  # Default: Jan 14, 2025
            
            # Storage settings
            'storage_base_dir': 'data',
        }
        
        # Validate required settings
        required = ['smtp_host', 'smtp_user', 'smtp_password', 'from_email']
        missing = [key for key in required if not config.get(key)]
        
        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")
        
        if not config['to_emails']:
            raise ValueError("No receiver emails configured in 'receiver_emails'")
        
        return config
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in configuration file: {e}")


def identify_new_urls_per_source(all_urls: Dict[str, List[str]], 
                                  storage: MultiSourceStorage) -> Dict[str, List[str]]:
    """Identify URLs that haven't been seen before for each source."""
    new_urls = {}
    
    for source, urls in all_urls.items():
        seen_urls = storage.get_seen_urls_for_source(source)
        new_for_source = [url for url in urls if url not in seen_urls]
        if new_for_source:
            new_urls[source] = new_for_source
    
    return new_urls


def main():
    """Main execution function."""
    # Use single log file that appends
    logger = setup_logging(log_file="scraper.log")
    
    logger.info("")
    logger.info("=" * 60)
    logger.info(f"Starting Daily URL Scraper - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    try:
        # Load configuration
        logger.info("Loading configuration from config/email_config.json...")
        config = load_config()
        logger.info("Configuration loaded successfully")
        logger.info(f"Email will be sent to: {', '.join(config['to_emails'])}")
        logger.info(f"Date filter: Only URLs from {config['filter_date']} onwards")
        
        # Initialize components
        storage = MultiSourceStorage(config['storage_base_dir'])
        scraper = URLScraper(
            timeout=config['timeout'],
            max_retries=config['max_retries'],
            filter_date=config['filter_date']  # Pass date filter to scraper
        )
        email_sender = EmailSender(
            smtp_host=config['smtp_host'],
            smtp_port=config['smtp_port'],
            smtp_user=config['smtp_user'],
            smtp_password=config['smtp_password'],
            from_email=config['from_email'],
            use_ssl=config['use_ssl']
        )
        
        # Display current stats
        logger.info("Current storage statistics:")
        all_stats = storage.get_all_stats()
        for source, stats in all_stats.items():
            logger.info(f"  {source}: {stats['total_urls']} URLs in {Path(stats['file']).name}")
        
        combined_stats = storage.get_combined_stats()
        logger.info(f"Total URLs across all sources: {combined_stats['total_urls_across_all_sources']}")
        
        # Scrape all sources
        logger.info("Starting URL scraping from all sources...")
        all_urls = scraper.scrape_all_sources()
        
        total_scraped = sum(len(urls) for urls in all_urls.values())
        logger.info(f"Total URLs scraped (after date filtering): {total_scraped}")
        
        # Identify new URLs per source
        new_urls = identify_new_urls_per_source(all_urls, storage)
        total_new = sum(len(urls) for urls in new_urls.values())
        
        logger.info(f"New URLs found: {total_new}")
        
        # Update storage for each source
        for source, urls in all_urls.items():
            if urls:
                new_count = storage.add_urls_for_source(source, urls)
                logger.info(f"  {source}: {new_count} new URLs added")
        
        # Send email notification to all receivers
        logger.info(f"Sending email notifications to {len(config['to_emails'])} recipient(s)...")
        
        email_success_count = 0
        for to_email in config['to_emails']:
            logger.info(f"Sending to {to_email}...")
            if email_sender.send_email(
                to_email=to_email,
                new_urls=new_urls,
                total_new=total_new
            ):
                email_success_count += 1
                logger.info(f"Email sent successfully to {to_email}")
            else:
                logger.error(f"Failed to send email to {to_email}")
        
        logger.info(f"Email delivery: {email_success_count}/{len(config['to_emails'])} successful")
        
        # Display summary
        logger.info("=" * 60)
        logger.info("Summary:")
        for source, urls in new_urls.items():
            logger.info(f"  {source}: {len(urls)} new URLs")
        logger.info(f"Total new URLs: {total_new}")
        logger.info("")
        logger.info("Storage files updated:")
        for source in all_urls.keys():
            storage_obj = storage.get_storage_for_source(source)
            logger.info(f"  {source}: {storage_obj.storage_path}")
        logger.info("=" * 60)
        logger.info(f"Completed - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        # Close scraper session
        scraper.close()
        
        return 0
        
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())