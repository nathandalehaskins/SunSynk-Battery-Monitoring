import yaml
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SiteValidation:
    exists: bool = False
    id_matches: bool = False
    has_inverters: bool = False
    status: str = 'invalid'
    inverter_sn: Optional[str] = None
    inverter_type: Optional[str] = None
    site_id: Optional[str] = None

class SiteValidator:
    def __init__(self, sites_config_path: str, all_sites_data: Dict):
        self.sites_config_path = sites_config_path
        self.all_sites_data = all_sites_data
        self.load_sites_config()

    def load_sites_config(self):
        with open(self.sites_config_path, 'r') as file:
            self.sites_config = yaml.safe_load(file)

    def validate_sites(self) -> Dict[str, SiteValidation]:
        results = {}
        logger.info(f"Starting site validation with {len(self.all_sites_data)} sites")
        logger.debug(f"Available sites: {list(self.all_sites_data.keys())}")
        logger.debug(f"First site data example: {next(iter(self.all_sites_data.items()), None)}")
        
        # First, create a mapping of site_id to site_data
        site_id_map = {
            str(site_data['id']): {'name': site_name, 'data': site_data}
            for site_name, site_data in self.all_sites_data.items()
        }
        logger.debug(f"Created site ID mapping with {len(site_id_map)} entries")
        
        for site in self.sites_config.get('sla_sites', []):
            site_name = site['name']
            site_id = str(site['site_id'])
            logger.info(f"Validating site: {site_name} (ID: {site_id})")
            
            validation = SiteValidation()
            validation.site_id = site_id
            if site_id in site_id_map:
                logger.debug(f"Site ID {site_id} found in available sites")
                validation.exists = True
                site_data = site_id_map[site_id]['data']
                actual_name = site_id_map[site_id]['name']
                validation.id_matches = True
                
                if 'inverters' in site_data:
                    logger.debug(f"Found {len(site_data['inverters'])} inverters for site {site_name}")
                    for sn, inv_type in site_data['inverters'].items():
                        logger.debug(f"Checking inverter SN: {sn}, Type: {inv_type}")
                        if inv_type in ['M', 'M1'] or inv_type is None:
                            validation.has_inverters = True
                            validation.inverter_sn = sn
                            validation.inverter_type = inv_type or 'M'
                            validation.status = 'valid'
                            logger.info(f"Valid inverter found for {site_name} - SN: {sn}, Type: {validation.inverter_type}")
                            break
                else:
                    logger.warning(f"No inverters found for site {site_name}")
            else:
                logger.warning(f"Site ID {site_id} ({site_name}) not found in available sites")
            
            results[site_name] = validation
            logger.info(f"Validation result for {site_name}: {validation}")
        
        valid_count = sum(1 for v in results.values() if v.status == 'valid')
        logger.info(f"Validation complete - Found {valid_count}/{len(results)} valid sites")
        return results