import aiohttp
import asyncio
from aiolimiter import AsyncLimiter
import logging
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)

class SunSynkAPI:
    def __init__(self, config: Dict):
        self.base_url = config['api']['sunsynk']['base_url']
        self.rate_limit = AsyncLimiter(config['api']['sunsynk']['rate_limit'], 1)
        self.max_retries = config['api']['sunsynk']['max_retries']
        self.retry_delay = config['api']['sunsynk']['retry_delay']
        
    async def get_token(self, session: aiohttp.ClientSession, username: str, password: str) -> Tuple[Optional[str], Optional[int]]:
        """Reference to original token fetch logic"""
        # Reference to original implementation:
        """python:STEP1_fetch_site_details_and_SN.py
        startLine: 25
        endLine: 51
        """
        url = f'{self.base_url}/oauth/token'
        headers = {
            'accept': 'application/json',
            'content-type': 'application/json',
        }
        payload = {
            'areaCode': 'sunsynk',
            'client_id': 'csp-web',
            'grant_type': 'password',
            'password': password,
            'source': 'sunsynk',
            'username': username,
        }
        
        try:
            async with session.post(url, json=payload, headers=headers) as response:
                data = await response.json()
                if data['success'] and 'data' in data:
                    return data['data']['access_token'], data['data']['expires_in']
                logger.error(f"Failed to acquire token. Error message: {data.get('msg', 'Unknown error')}")
        except Exception as e:
            logger.error(f"An error occurred while getting the token: {e}")
        return None, None

    async def get_plants(self, session: aiohttp.ClientSession, access_token: str, page: int, limit: int = 14) -> Optional[Dict]:
        """Reference to original plants fetch logic"""
        # Reference to original implementation:
        """python:STEP1_fetch_site_details_and_SN.py
        startLine: 53
        endLine: 81
        """
        url = f'{self.base_url}/api/v1/plants?page={page}&limit={limit}'
        headers = {
            'accept': 'application/json',
            'Authorization': f'Bearer {access_token}',
        }
        
        for attempt in range(self.max_retries):
            async with self.rate_limit:
                try:
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            return await response.json()
                        logger.error(f"Failed to fetch plant list for page {page}. Status: {response.status}")
                except Exception as e:
                    logger.error(f"Exception in get_plants for page {page}: {e}")
                
                if attempt < self.max_retries - 1:
                    delay = (attempt + 1) * 2
                    logger.info(f"Retrying page {page} in {delay} seconds...")
                    await asyncio.sleep(delay)
        
        return None

    async def get_site_inverters(self, session: aiohttp.ClientSession, access_token: str, site_id: int) -> Optional[Dict]:
        """Get inverters for a specific site"""
        url = f"{self.base_url}/api/v1/plant/{site_id}/inverters"
        params = {
            'page': 1,
            'limit': 10,
            'status': -1,
            'sn': '',
            'id': site_id,
            'type': -2
        }
        
        async with self.rate_limit:
            try:
                async with session.get(url, params=params, headers={'Authorization': f'Bearer {access_token}'}) as response:
                    data = await response.json()
                    if 'data' in data and 'infos' in data['data']:
                        return {
                            inverter['sn']: inverter.get('equipMode', None) 
                            for inverter in data['data']['infos']
                        }
                    logger.warning(f"No inverter data found for site {site_id}")
                    return {}
            except Exception as e:
                logger.error(f"Failed to fetch inverters for site {site_id}. Error: {e}")
                return None

    async def get_all_sites(self, session: aiohttp.ClientSession, access_token: str) -> Dict:
        """Fetch all sites data including inverter information"""
        all_sites_data = {}
        total_pages = 14

        # Fetch all plants first
        plant_tasks = [self.get_plants(session, access_token, page) 
                      for page in range(1, total_pages + 1)]
        plants_info_list = await asyncio.gather(*plant_tasks)
        
        # Process plants and fetch inverters
        for plants_info in plants_info_list:
            if plants_info and isinstance(plants_info, dict) and 'data' in plants_info and 'infos' in plants_info['data']:
                for plant in plants_info['data']['infos']:
                    site_name = plant['name']
                    site_id = plant['id']
                    
                    # Fetch inverters for this site
                    inverters = await self.get_site_inverters(session, access_token, site_id)
                    
                    all_sites_data[site_name] = {
                        'id': site_id,
                        'inverters': inverters if inverters is not None else {}
                    }
        
        return all_sites_data