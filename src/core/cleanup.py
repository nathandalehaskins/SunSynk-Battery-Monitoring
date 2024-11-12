import os
import time
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class DataCleanupManager:
    def __init__(self, config: dict):
        self.config = config
        self.retention_periods = {
            'data/raw': timedelta(days=7),
            'data/processed': timedelta(days=7),
            'data/cache': timedelta(days=1),
            'logs': timedelta(days=7)
        }

    def cleanup_old_data(self):
        """Cleanup old data files and logs"""
        logger.info("Starting data cleanup process")
        
        for directory, retention_period in self.retention_periods.items():
            if not os.path.exists(directory):
                continue
                
            current_time = datetime.now()
            for filename in os.listdir(directory):
                filepath = os.path.join(directory, filename)
                if filename.startswith('.'):  # Skip .gitkeep files
                    continue
                    
                file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                if current_time - file_time > retention_period:
                    try:
                        os.remove(filepath)
                        logger.info(f"Removed old file: {filepath}")
                    except Exception as e:
                        logger.error(f"Error removing {filepath}: {e}")
