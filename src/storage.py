"""
Storage module for managing seen URLs in JSON format.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Set, List

logger = logging.getLogger(__name__)


class URLStorage:
    """Handles persistence of discovered URLs."""
    
    def __init__(self, storage_path: str = "data/seen_urls.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_storage_file()
    
    def _ensure_storage_file(self):
        """Create storage file if it doesn't exist."""
        if not self.storage_path.exists():
            self._save_data({"urls": {}, "last_updated": None})
            logger.info(f"Created new storage file: {self.storage_path}")
    
    def _load_data(self) -> Dict:
        """Load data from JSON file."""
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {self.storage_path}: {e}")
            return {"urls": {}, "last_updated": None}
        except Exception as e:
            logger.error(f"Error loading storage file {self.storage_path}: {e}")
            return {"urls": {}, "last_updated": None}
    
    def _save_data(self, data: Dict):
        """Save data to JSON file."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved data to {self.storage_path}")
        except Exception as e:
            logger.error(f"Error saving storage file {self.storage_path}: {e}")
            raise
    
    def get_seen_urls(self) -> Set[str]:
        """Get all previously seen URLs."""
        data = self._load_data()
        return set(data.get("urls", {}).keys())
    
    def add_urls(self, urls: List[str], source: str = "unknown"):
        """Add new URLs to storage with metadata."""
        data = self._load_data()
        timestamp = datetime.now().isoformat()
        
        new_count = 0
        for url in urls:
            if url not in data["urls"]:
                data["urls"][url] = {
                    "first_seen": timestamp,
                    "source": source
                }
                new_count += 1
        
        data["last_updated"] = timestamp
        self._save_data(data)
        
        logger.info(f"Added {new_count} new URLs to {self.storage_path.name}")
        return new_count
    
    def get_stats(self) -> Dict:
        """Get statistics about stored URLs."""
        data = self._load_data()
        urls = data.get("urls", {})
        
        sources = {}
        for url_data in urls.values():
            source = url_data.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
        
        return {
            "total_urls": len(urls),
            "last_updated": data.get("last_updated"),
            "sources": sources,
            "file": str(self.storage_path)
        }
    
    def get_all_urls(self) -> Dict[str, Dict]:
        """Get all URLs with their metadata."""
        data = self._load_data()
        return data.get("urls", {})


class MultiSourceStorage:
    """Manages multiple storage files for different sources."""
    
    def __init__(self, base_dir: str = "data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage for each source
        self.storages = {
            "dexpose.io": URLStorage(str(self.base_dir / "dexpose_urls.json")),
            "ransomware.live": URLStorage(str(self.base_dir / "ransomware_live_urls.json")),
            "redpacketsecurity.com": URLStorage(str(self.base_dir / "redpacket_security_urls.json"))
        }
        
        logger.info(f"Initialized storage for {len(self.storages)} sources in {self.base_dir}")
    
    def get_storage_for_source(self, source: str) -> URLStorage:
        """Get storage instance for a specific source."""
        if source not in self.storages:
            raise ValueError(f"Unknown source: {source}. Available: {list(self.storages.keys())}")
        return self.storages[source]
    
    def get_seen_urls_for_source(self, source: str) -> Set[str]:
        """Get previously seen URLs for a specific source."""
        storage = self.get_storage_for_source(source)
        return storage.get_seen_urls()
    
    def add_urls_for_source(self, source: str, urls: List[str]) -> int:
        """Add URLs for a specific source."""
        storage = self.get_storage_for_source(source)
        return storage.add_urls(urls, source)
    
    def get_all_stats(self) -> Dict:
        """Get statistics for all sources."""
        stats = {}
        for source, storage in self.storages.items():
            stats[source] = storage.get_stats()
        return stats
    
    def get_combined_stats(self) -> Dict:
        """Get combined statistics across all sources."""
        total_urls = 0
        all_sources = {}
        last_updates = []
        
        for source, storage in self.storages.items():
            source_stats = storage.get_stats()
            total_urls += source_stats["total_urls"]
            all_sources[source] = source_stats["total_urls"]
            if source_stats["last_updated"]:
                last_updates.append(source_stats["last_updated"])
        
        return {
            "total_urls_across_all_sources": total_urls,
            "urls_per_source": all_sources,
            "last_updated": max(last_updates) if last_updates else None,
            "number_of_sources": len(self.storages)
        }