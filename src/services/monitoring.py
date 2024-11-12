import asyncio
import logging
from datetime import datetime, time
from typing import Dict, Optional
from src.api.sunsynk import SunSynkAPI
from src.core.fetcher import DataFetcher
from src.core.analyzer import DataAnalyzer
from src.api.google_sheets import GoogleSheetsPublisher
from src.validators.site_validator import SiteValidator
from src.core.cleanup import DataCleanupManager

logger = logging.getLogger(__name__)

class MonitoringService:
    def __init__(self, config: Dict):
        self.config = config
        self.api = SunSynkAPI(config)
        self.fetcher = DataFetcher(config)
        self.analyzer = DataAnalyzer(config)
        self.publisher = GoogleSheetsPublisher(config)
        self.validated_sites = {}  # Cache for validated sites
        
        self.site_refresh_time = time(5, 0)  # 5 AM
        self.data_fetch_interval = config['monitoring']['fetch_interval']  # Get from config
        
        self.cleanup_manager = DataCleanupManager(config)
        
    async def _refresh_site_data(self):
        """Daily refresh of site and inverter data"""
        try:
            logger.info(f"Starting daily site data refresh at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("Fetching all sites from SunSynk API...")
            all_sites = await self.fetcher.fetch_all_sites()
            logger.info(f"Retrieved {len(all_sites)} total sites from API")
            
            # Update validator and cache
            self.fetcher.validator = SiteValidator(self.config['sites_config'], all_sites)
            self.fetcher._save_to_cache(all_sites)
            
            logger.info("Starting site validation process...")
            self.validated_sites = self.fetcher.validator.validate_sites()
            logger.info(f"Validation complete - Found {len(self.validated_sites)} configured sites")
            
            # Save to data/raw directory
            logger.info("Saving raw site data to disk...")
            self.fetcher.save_data(all_sites, 'data/raw/all_sites_data.json')
            logger.info("Daily site data refresh completed successfully")
            return all_sites
        except Exception as e:
            logger.error(f"Error in site data refresh: {str(e)}", exc_info=True)
            return None

    async def _fetch_and_process_data(self):
        """Fetch current data, analyze, and publish"""
        try:
            # Fetch current inverter data
            current_data = await self.fetcher.fetch_data()
            if not current_data:
                logger.error("No data fetched from inverters")
                return

            # Save raw data
            self.fetcher.save_data(current_data, 'data/raw/fetched_inverter_data.json')

            # Analyze the data
            analysis_results = self.analyzer.analyze(current_data)
            self.fetcher.save_data(analysis_results, 'data/processed/analysis_results.json')

            # Publish to Google Sheets
            await self.publisher.publish(analysis_results)
            
        except Exception as e:
            logger.error(f"Error in fetch and process cycle: {e}")

    async def _should_refresh_sites(self) -> bool:
        """Check if it's time for daily site refresh"""
        now = datetime.now().time()
        should_refresh = now.hour == self.site_refresh_time.hour and now.minute == self.site_refresh_time.minute
        logger.debug(f"Checking refresh time - Current: {now.strftime('%H:%M')}, Target: {self.site_refresh_time.strftime('%H:%M')}, Should refresh: {should_refresh}")
        return should_refresh

    async def run(self):
        """Main service loop"""
        logger.info("Starting monitoring service")
        
        while True:
            try:
                # Run cleanup daily at 4 AM (before site refresh)
                now = datetime.now().time()
                if now.hour == 4 and now.minute == 0:
                    self.cleanup_manager.cleanup_old_data()
                
                # Check for daily site refresh
                if await self._should_refresh_sites():
                    await self._refresh_site_data()

                # Regular data fetch and processing cycle
                await self._fetch_and_process_data()
                
                # Wait for next cycle
                await asyncio.sleep(self.data_fetch_interval)
                
            except Exception as e:
                logger.error(f"Error in main service loop: {e}")
                await asyncio.sleep(60)  # Wait a minute before retrying