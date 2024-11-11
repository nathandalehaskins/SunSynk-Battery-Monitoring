import asyncio
import aiohttp
import logging
from typing import Dict, Optional, List
from datetime import datetime
from ..api.sunsynk import SunSynkAPI
from ..validators.site_validator import SiteValidator
from aiolimiter import AsyncLimiter
from datetime import timedelta
import json
import os
from ..core.analyzer import SiteAnalysis

logger = logging.getLogger(__name__)

class DataFetcher:
    def __init__(self, config: Dict):
        self.config = config
        self.api = SunSynkAPI(config)
        self.validator = None
        self.rate_limit = AsyncLimiter(20, 1)
        self.cache_file = 'data/cache/site_validator_cache.json'
        self.last_refresh_file = 'data/cache/last_refresh.txt'
        
        # Create cache directory if it doesn't exist
        os.makedirs('data/cache', exist_ok=True)
        
        # Try to load cached validator
        self._load_cached_validator()

    def _load_cached_validator(self):
        """Load cached validator if it exists and is from today"""
        try:
            if os.path.exists(self.last_refresh_file):
                with open(self.last_refresh_file, 'r') as f:
                    last_refresh = datetime.fromisoformat(f.read().strip())
                    
                # Only use cache if it's from today
                if last_refresh.date() == datetime.now().date():
                    logger.info("Found valid cache from today")
                    if os.path.exists(self.cache_file):
                        with open(self.cache_file, 'r') as f:
                            cached_data = json.load(f)
                            self.validator = SiteValidator(self.config['sites_config'], cached_data)
                            logger.info("Successfully loaded cached validator")
                            return
            
            logger.info("No valid cache found or cache is outdated")
        except Exception as e:
            logger.error(f"Error loading cache: {e}")

    def _save_to_cache(self, data: Dict):
        """Save validator data to cache"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(data, f)
            with open(self.last_refresh_file, 'w') as f:
                f.write(datetime.now().isoformat())
            logger.info("Successfully saved data to cache")
        except Exception as e:
            logger.error(f"Error saving to cache: {e}")

    async def _get_all_sites(self, session: aiohttp.ClientSession, access_token: str) -> Dict:
        """Fetch all sites data - reference to original implementation"""
        # Reference to original implementation:
        """python:STEP1_fetch_site_details_and_SN.py
        startLine: 114
        endLine: 156
        """
        all_sites_data = {}
        total_pages = 14

        plant_tasks = [self.api.get_plants(session, access_token, page) 
                      for page in range(1, total_pages + 1)]
        plants_info_list = await asyncio.gather(*plant_tasks)
        
        for plants_info in plants_info_list:
            if plants_info and isinstance(plants_info, dict) and 'data' in plants_info and 'infos' in plants_info['data']:
                for plant in plants_info['data']['infos']:
                    site_name = plant['name']
                    site_id = plant['id']
                    all_sites_data[site_name] = {'id': site_id}
        
        return all_sites_data

    async def _get_site_inverters(self, session: aiohttp.ClientSession, access_token: str, 
                                site_name: str, site_id: int) -> Optional[Dict]:
        """Fetch inverters for a specific site"""
        inverters = await self.api.get_site_inverters(session, access_token, site_id)
        if inverters is not None:
            return {
                'id': site_id,
                'inverters': inverters
            }
        return None

    async def _fetch_inverter_data(self, session: aiohttp.ClientSession, access_token: str, 
                                 sn: str, site_name: str, site_id: int, inverter_type: str) -> Dict:
        """Fetch data for a specific inverter"""
        today = datetime.today().strftime('%Y-%m-%d')
        # params=16,18,106 includes SOC, V-bat, and BMS Voltage
        full_url = f"https://api.sunsynk.net/api/v1/inverter/{sn}/day?sn={sn}&date={today}&edate={today}&lan=en&params=16,18,106"
        
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        async with self.rate_limit:
            try:
                async with session.get(full_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.debug(f"Raw data for {site_name}: {data}")
                        logger.info(f"Data fetched successfully for {site_name}")
                        
                        # Fetch yesterday's max SOC
                        yesterday_max_soc = await self._fetch_yesterday_data(session, access_token, sn)
                        logger.info(f"Yesterday's max SOC for {site_name}: {yesterday_max_soc}")
                        
                        return {
                            'site_id': site_id,
                            'inverter_sn': sn,
                            'inverter_type': inverter_type,
                            'data': data,
                            'yesterday_max_soc': yesterday_max_soc
                        }
                    else:
                        logger.error(f"Failed to fetch data for {site_name}. Status: {response.status}")
                        return None
            except Exception as e:
                logger.error(f"Error fetching data for {site_name}: {e}")
                return None
    
            
    async def fetch_data(self) -> Dict:
        """Fetch current data for all validated sites"""
        logger.info("Starting data fetch cycle...")
        
        # Only fetch sites if validator isn't initialized
        if self.validator is None:
            logger.info("No cached validator found. Performing initial site refresh...")
            all_sites = await self.fetch_all_sites()
            if not all_sites:
                logger.error("Failed to fetch initial sites data")
                return {}
            self.validator = SiteValidator(self.config['sites_config'], all_sites)
            self._save_to_cache(all_sites)

        connector = aiohttp.TCPConnector(ssl=False, limit=50)  # Increased connection limit
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            try:
                logger.info("Authenticating with SunSynk API...")
                access_token, _ = await self.api.get_token(
                    session, 
                    self.config['api']['sunsynk']['username'],
                    self.config['api']['sunsynk']['password']
                )
                
                if not access_token:
                    logger.error("Failed to obtain access token")
                    return {}

                logger.info("Successfully obtained access token")
                results = {}
                
                validated_sites = self.validator.validate_sites()
                logger.info(f"Found {sum(1 for v in validated_sites.values() if v.status == 'valid')} valid sites to process")
                
                for site_name, validation in validated_sites.items():
                    if validation.status == 'valid':
                        logger.info(f"Fetching data for site: {site_name} (SN: {validation.inverter_sn})")
                        try:
                            data = await self._fetch_inverter_data(
                                session, 
                                access_token,
                                validation.inverter_sn,
                                site_name,
                                validation.site_id,
                                validation.inverter_type
                            )
                            if data:
                                results[site_name] = data
                        except Exception as e:
                            logger.error(f"Error fetching data for {site_name}: {str(e)}", exc_info=True)
                    else:
                        logger.warning(f"Skipping invalid site: {site_name}")
                
                logger.info(f"Data fetch cycle complete - Processed {len(results)} sites")
                return results
                
            except Exception as e:
                logger.error(f"Fatal error in fetch_data: {str(e)}", exc_info=True)
                return {}
        
    def save_data(self, data: Dict, filepath: str):
        """Save data to a JSON file"""
        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Convert SiteAnalysis objects to dict if needed
            if any(isinstance(v, SiteAnalysis) for v in data.values()):
                data = self._convert_analysis_to_dict(data)
                
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=4)
            logger.debug(f"Data saved to {filepath}")
        except Exception as e:
            logger.error(f"Error saving data to {filepath}: {e}")
        
    def _convert_analysis_to_dict(self, analysis_results: Dict) -> Dict:
        """Convert SiteAnalysis objects to dictionary for JSON serialization"""
        return {
            site_name: {
                'site_id': analysis.site_id,
                'inverter_sn': analysis.inverter_sn,
                'inverter_type': analysis.inverter_type,
                'lowest_soc': analysis.lowest_soc,
                'lowest_soc_time': analysis.lowest_soc_time,
                'current_soc': analysis.current_soc,
                'current_soc_time': analysis.current_soc_time,
                'max_v_diff': analysis.max_v_diff,
                'max_diff_time': analysis.max_diff_time,
                'max_v_bat': analysis.max_v_bat,
                'max_v_bat_time': analysis.max_v_bat_time,
                'current_v_bat': analysis.current_v_bat,
                'current_vbms': analysis.current_vbms,
                'current_voltage_time': analysis.current_voltage_time
            }
            for site_name, analysis in analysis_results.items()
        }
        
    async def _fetch_yesterday_data(self, session: aiohttp.ClientSession, access_token: str, 
                                  sn: str) -> Optional[float]:
        """Fetch yesterday's SOC data"""
        yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        url = f"https://api.sunsynk.net/api/v1/inverter/{sn}/day?sn={sn}&date={yesterday}&edate={yesterday}&lan=en&params=16"
        
        async with self.rate_limit:
            try:
                async with session.get(url, headers={'Authorization': f'Bearer {access_token}'}) as response:
                    if response.status == 200:
                        data = await response.json()
                        soc_records = next((info['records'] for info in data['data']['infos'] 
                                         if info['label'] == 'SOC'), [])
                        if soc_records:
                            return max(float(record['value']) for record in soc_records)
                    return None
            except Exception as e:
                logger.error(f"Error fetching yesterday's data for {sn}: {e}")
                return None
        
    async def fetch_all_sites(self) -> Dict:
        """Fetch all sites data"""
        logger.info("Starting to fetch all sites")
        connector = aiohttp.TCPConnector(ssl=False, limit=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            # Get token
            access_token, _ = await self.api.get_token(
                session, 
                self.config['api']['sunsynk']['username'],
                self.config['api']['sunsynk']['password']
            )
            
            if not access_token:
                logger.error("Failed to acquire access token")
                return {}

            logger.info("Successfully obtained access token, fetching sites...")
            # Use the API's get_all_sites method directly
            all_sites = await self.api.get_all_sites(session, access_token)
            
            if not all_sites:
                logger.error("No sites returned from API")
                return {}
                
            logger.info(f"Successfully fetched {len(all_sites)} sites with inverter data")
            return all_sites
        
        