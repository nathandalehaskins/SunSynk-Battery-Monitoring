import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class SiteAnalysis:
    site_id: str
    inverter_sn: str
    inverter_type: str
    lowest_soc: str
    lowest_soc_time: Optional[str]
    current_soc: str
    current_soc_time: Optional[str]
    max_v_diff: Optional[float]
    max_diff_time: Optional[str]
    max_v_bat: Optional[float]
    max_v_bat_time: Optional[str]
    current_v_bat: Optional[float]
    current_vbms: Optional[float]
    current_voltage_time: Optional[str]
    yesterday_max_soc: Optional[float]

class DataAnalyzer:
    def __init__(self, config: Dict):
        self.config = config

    def _extract_records(self, data: List[Dict], label: str) -> List[Dict]:
        """Extract records for a specific label from data"""
        for info in data:
            if info['label'] == label:
                return info.get('records', [])
        return []

    def _analyze_site(self, site_name: str, site_info: Dict) -> SiteAnalysis:
        """Analyze data for a single site"""
        site_id = site_info['site_id']
        inverter_sn = site_info['inverter_sn']
        inverter_type = site_info['inverter_type']
        data = site_info['data']['data']['infos']
        yesterday_max_soc = site_info.get('yesterday_max_soc')

        analysis = SiteAnalysis(
            site_id=str(site_id),
            inverter_sn=inverter_sn,
            inverter_type=inverter_type,
            lowest_soc="OFFLINE",
            lowest_soc_time=None,
            current_soc="OFFLINE",
            current_soc_time=None,
            max_v_diff=None,
            max_diff_time=None,
            max_v_bat=None,
            max_v_bat_time=None,
            current_v_bat=None,
            current_vbms=None,
            current_voltage_time=None,
            yesterday_max_soc=yesterday_max_soc
        )

        soc_records = next((info['records'] for info in data if info['label'] == 'SOC'), [])
        v_bat_records = next((info['records'] for info in data if info['label'] == 'V-bat'), [])
        vbms_records = next((info['records'] for info in data if info['label'] == 'BMS Voltage'), [])

        if soc_records:
            lowest_soc_record = min(soc_records, key=lambda x: float(x['value']))
            current_soc_record = soc_records[-1]
            analysis.lowest_soc = lowest_soc_record['value']
            analysis.lowest_soc_time = lowest_soc_record['time']
            analysis.current_soc = current_soc_record['value']
            analysis.current_soc_time = current_soc_record['time']

        if v_bat_records and vbms_records:
            # Get current readings
            current_v_bat_record = v_bat_records[-1]
            current_vbms_record = vbms_records[-1]
            analysis.current_v_bat = float(current_v_bat_record['value'])
            analysis.current_vbms = float(current_vbms_record['value'])
            analysis.current_voltage_time = current_v_bat_record['time']
            
            # Calculate max voltage difference
            for v_bat_rec, vbms_rec in zip(v_bat_records, vbms_records):
                v_bat_value = float(v_bat_rec['value'])
                vbms_value = float(vbms_rec['value'])
                diff = abs(v_bat_value - vbms_value)
                
                if analysis.max_v_diff is None or diff > analysis.max_v_diff:
                    analysis.max_v_diff = diff
                    analysis.max_diff_time = v_bat_rec['time']
                    analysis.max_v_bat = v_bat_value
                    analysis.max_v_bat_time = v_bat_rec['time']

        return analysis

    def analyze(self, fetched_data: Dict) -> Dict[str, SiteAnalysis]:
        """Analyze all fetched data"""
        analysis_results = {}
        
        for site_name, site_info in fetched_data.items():
            try:
                analysis = self._analyze_site(site_name, site_info)
                analysis_results[site_name] = analysis
                logger.info(f"Analysis completed for site: {site_name}")
            except Exception as e:
                logger.error(f"Error analyzing site {site_name}: {str(e)}")
                continue

        return analysis_results