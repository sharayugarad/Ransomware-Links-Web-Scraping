# Daily Ransomware URL Scraper - Project Documentation

## 1. Project Overview

This project is an automated Python tool that monitors ransomware-related websites, scrapes newly published URLs, stores them for deduplication, and sends daily email reports to designated team members. It serves as a lightweight threat intelligence feed for tracking ransomware activity across multiple open sources.

**Version:** 1.0.0
**Language:** Python 3.12+
**Last Updated:** March 2026

---

## 2. What Problem Does It Solve?

Security teams need to stay aware of new ransomware-related web pages (group profiles, breach disclosures, negotiation pages, etc.). Manually checking multiple websites daily is tedious and error-prone. This tool automates that process by:

- Scraping 3 ransomware intelligence sources on each run
- Filtering URLs by date to only capture recent activity
- Deduplicating against previously seen URLs
- Emailing a summary of newly discovered URLs to the team

---

## 3. Architecture

```
┌─────────────┐
│   run.py    │  Entry point
└──────┬──────┘
       │
       v
┌──────────────────────────────────────────────────────┐
│                    src/main.py                       │
│               (Orchestration Layer)                  │
│                                                      │
│  1. Load config    2. Scrape    3. Deduplicate       │
│  4. Store          5. Email    6. Log                │
└──────┬───────────────┬───────────────┬───────────────┘
       │               │               │
       v               v               v
┌─────────────┐ ┌─────────────┐ ┌──────────────┐
│ scraper.py  │ │ storage.py  │ │email_sender.py│
│  (Fetching  │ │  (JSON-based│ │  (SMTP email  │
│  & Parsing) │ │  persistence│ │  notification)│
└─────────────┘ └─────────────┘ └──────────────┘
       │               │
       v               v
  3 Web Sources    data/*.json
```

---

## 4. Data Sources

| Source | URL | Method | Content |
|--------|-----|--------|---------|
| dexpose.io | `https://dexpose.io/sitemap-0.xml` | XML sitemap parsing | Breach monitoring, dark web API pages |
| ransomware.live | `https://www.ransomware.live/sitemap.xml` | XML sitemap parsing | Ransomware group profiles, press, negotiations |
| redpacketsecurity.com | `https://www.redpacketsecurity.com/` | HTML link extraction | Security threat intelligence articles |

---

## 5. Project Structure

```
Ransomware-Links/
├── run.py                  # Entry point: python run.py
├── test_setup.py           # Validates environment before first run
├── requirements.txt        # Python dependencies
│
├── src/                    # Application source code
│   ├── __init__.py         # Package version (1.0.0)
│   ├── main.py             # Orchestrator - ties all modules together
│   ├── scraper.py          # Web scraper with retry logic & date filtering
│   ├── storage.py          # JSON file-based URL storage & deduplication
│   └── email_sender.py     # SMTP email notifications (HTML + plain text)
│
├── config/
│   └── email_config.json   # SMTP credentials, recipients, date filter
│
├── data/                   # Persisted URL data (JSON)
│   ├── dexpose_urls.json
│   ├── ransomware_live_urls.json
│   └── redpacket_security_urls.json
│
├── logs/
│   └── scraper.log         # Append-only execution log
│
└── DOCUMENTATION/
    └── PROJECT_OVERVIEW.md  # This file
```

---

## 6. Module Breakdown

### 6.1 `run.py` (Entry Point)

Adds `src/` to the Python path and calls `main()`. This is the only file you need to execute.

```
Usage: python run.py
```

### 6.2 `src/main.py` (Orchestrator)

Controls the full execution pipeline:

1. **Load config** from `config/email_config.json`
2. **Initialize** the scraper, storage, and email sender
3. **Scrape** all 3 sources
4. **Identify new URLs** by comparing against previously stored URLs
5. **Update storage** files with any new discoveries
6. **Send email** reports to all configured recipients
7. **Log** a summary to `logs/scraper.log`

Key functions:
- `setup_logging()` - Configures file + console logging (append mode)
- `load_config()` - Reads and validates the JSON config file
- `identify_new_urls_per_source()` - Set-based deduplication per source
- `main()` - Full pipeline execution, returns 0 on success, 1 on error

### 6.3 `src/scraper.py` (Web Scraper)

**Class: `URLScraper`**

Handles all HTTP fetching and parsing with these features:

- **User-Agent rotation**: 4 browser-like user agents to avoid 403 blocks
- **Retry logic**: Automatic retries with exponential backoff on HTTP 429/500/502/503/504
- **Date filtering**: Extracts dates from URL paths and XML `<lastmod>` tags; discards URLs older than the configured cutoff date
- **Polite scraping**: 2-second delay between sources

Date patterns recognized in URLs:
- `/YYYY/MM/DD/` (e.g., `/2026/01/14/`)
- `/YYYY-MM-DD` (e.g., `/2026-01-14`)
- `/YYYYMMDD` (e.g., `/20260114`)

If no date is found in a URL, it is included by default (conservative approach).

### 6.4 `src/storage.py` (Persistence)

**Class: `URLStorage`** - Manages a single JSON file per source.

Each URL is stored with metadata:
```json
{
  "urls": {
    "https://example.com/page": {
      "first_seen": "2026-01-16T19:53:13.362904",
      "source": "dexpose.io"
    }
  },
  "last_updated": "2026-03-13T04:23:42.095605"
}
```

**Class: `MultiSourceStorage`** - Manages all 3 source files and provides aggregate statistics.

Deduplication is set-based: a URL is only added if it does not already exist in the source's JSON file.

### 6.5 `src/email_sender.py` (Notifications)

**Class: `EmailSender`**

Sends MIME multipart emails containing both HTML and plain-text versions. The HTML version includes styled sections with clickable links grouped by source. Supports both STARTTLS (port 587) and SMTP_SSL (port 465).

### 6.6 `test_setup.py` (Environment Validator)

Verifies the environment is ready before the first run:
- Checks that `requests`, `beautifulsoup4`, and `lxml` are installed
- Validates `config/email_config.json` exists with all required fields
- Imports all project modules to catch missing dependencies
- Verifies the directory structure
- Optionally tests the SMTP connection

```
Usage: python test_setup.py
```

---

## 7. Configuration

All settings are in `config/email_config.json`:

| Field | Type | Description |
|-------|------|-------------|
| `smtp_server` | string | SMTP host (e.g., `smtp.gmail.com`) |
| `smtp_port` | int | SMTP port (`587` for TLS, `465` for SSL) |
| `use_ssl` | bool | `true` for SSL, `false` for STARTTLS |
| `sender_email` | string | The "from" email address |
| `sender_password` | string | SMTP password or Gmail App Password |
| `receiver_emails` | list | Array of recipient email addresses |
| `timeout` | int | HTTP request timeout in seconds |
| `max_retries` | int | Max retry attempts per HTTP request |
| `filter_date` | string | Only collect URLs from this date onward (YYYY-MM-DD) |

---

## 8. Execution Flow Diagram

```
Start
  │
  ├─ Load config/email_config.json
  │    └─ Validate required fields
  │
  ├─ Initialize components
  │    ├─ MultiSourceStorage (3 JSON files)
  │    ├─ URLScraper (HTTP session with retries)
  │    └─ EmailSender (SMTP credentials)
  │
  ├─ Scrape all sources
  │    ├─ dexpose.io        ──> Parse XML sitemap ──> Filter by date
  │    ├─ ransomware.live   ──> Parse XML sitemap ──> Filter by date
  │    └─ redpacketsecurity ──> Parse HTML links   ──> Filter by date
  │
  ├─ Deduplicate
  │    └─ For each source: new_urls = scraped - previously_stored
  │
  ├─ Update storage
  │    └─ Append new URLs with timestamp to data/*.json
  │
  ├─ Send emails
  │    └─ For each recipient: send HTML + text report
  │
  └─ Log summary to logs/scraper.log
```

---

## 9. Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| requests | 2.31.0 | HTTP client with session/retry support |
| beautifulsoup4 | 4.12.3 | HTML and XML parsing |
| lxml | 5.1.0 | Fast XML parser backend for BeautifulSoup |
| certifi | (transitive) | SSL certificate verification |
| charset-normalizer | (transitive) | Character encoding detection |
| idna | (transitive) | International domain name handling |
| urllib3 | (transitive) | HTTP connection pooling |
| soupsieve | (transitive) | CSS selector support for BeautifulSoup |

All dependencies are pinned in `requirements.txt` (generated via `pip-compile`).

---

## 10. How to Run

**First time setup:**
```bash
pip install -r requirements.txt
python test_setup.py          # Validate environment
```

**Configure email:** Edit `config/email_config.json` with valid SMTP credentials. For Gmail, use an App Password (not your regular password).

**Run the scraper:**
```bash
python run.py
```

**Schedule daily runs (optional):** Use cron (Linux/macOS) or Task Scheduler (Windows) to run `python run.py` once per day.

---

## 11. Resilience Features

| Feature | Implementation |
|---------|---------------|
| **Retry on failure** | Automatic retries with exponential backoff on HTTP 429, 500-504 |
| **User-Agent rotation** | 4 browser user agents; rotates on 403 Forbidden |
| **Connection pooling** | `requests.Session` reuses TCP connections |
| **Graceful degradation** | If one source fails, the others still run |
| **Deduplication** | Set-based comparison prevents duplicate URL storage |
| **Append-only logging** | Full audit trail in `logs/scraper.log` |
| **Config validation** | Fails fast with clear errors on missing/invalid config |

---

## 12. Data Volume

As of the latest run:
- **ransomware.live**: ~121,000 stored URLs (4.9 MB)
- **dexpose.io**: ~48 stored URLs (1.5 KB)
- **redpacketsecurity.com**: 0 URLs (source may be blocking requests)
- **Total**: ~121,000+ tracked URLs

---

## 13. Limitations and Notes

- **No scheduling built in**: Requires external scheduling (cron, Task Scheduler) for daily automation
- **No database**: Uses flat JSON files for storage; adequate for current scale but would benefit from a database if URL volume grows significantly
- **redpacketsecurity.com**: Currently returns 0 URLs, likely due to the site blocking automated requests or structural changes
- **No log rotation**: `scraper.log` appends indefinitely and should be rotated manually or via logrotate
- **Email password**: Must be configured manually in the config file before the email feature will work
