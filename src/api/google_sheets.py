from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging
import os
from typing import Dict, List, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleSheetsPublisher:
    def __init__(self, config: Dict):
        self.config = config
        self.sheet_id = config['api']['google_sheets']['sheet_id']
        self.sheet_name = config['api']['google_sheets']['sheet_name']
        
        self.credentials_file = config['api']['google_sheets']['credentials_file']
        
        if not os.path.exists(self.credentials_file):
            logger.error(f"Credentials file not found: {self.credentials_file}")
            raise FileNotFoundError(f"Google Sheets credentials file not found: {self.credentials_file}")
            
        self.credentials = Credentials.from_service_account_file(
            self.credentials_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        self.service = build('sheets', 'v4', credentials=self.credentials)

    def _extract_time(self, datetime_str: str) -> str:
        """Extract time from datetime string"""
        if datetime_str:
            return datetime_str.split(" ")[1][:5]
        return None

    async def publish(self, data: Dict[str, Any]) -> None:
        try:
            # First clear the entire sheet
            clear_range = f"{self.sheet_name}!A1:K1000"  # Adjust range as needed
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=clear_range
            ).execute()
            
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Update the timestamp in A1
            timestamp_range = f"{self.sheet_name}!A1:B1"
            timestamp_value = [["Last Updated:", current_time]]
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=timestamp_range,
                valueInputOption="RAW",
                body={"values": timestamp_value}
            ).execute()
            
            # Define headers (starting from row 2)
            headers = [
                ["Site Name", "Inverter SN", "Lowest SOC", "Lowest Time", "Current SOC", 
                 "Current Time", "V-bat", "V-BMS", "V-Diff", "Voltage Time", "Yesterday Max SOC"]
            ]
            
            # Create data rows
            data_rows = []
            for site_name, site_data in data.items():
                status = 'OFFLINE' if site_data.current_soc == 'OFFLINE' else 'ONLINE'
                row = [
                    site_name,
                    site_data.inverter_sn,
                    site_data.lowest_soc,
                    self._extract_time(site_data.lowest_soc_time),
                    site_data.current_soc,
                    self._extract_time(site_data.current_soc_time),
                    f"{site_data.current_v_bat:.2f}" if site_data.current_v_bat is not None else 'N/A',
                    f"{site_data.current_vbms:.2f}" if site_data.current_vbms is not None else 'N/A',
                    f"{site_data.max_v_diff:.2f}" if site_data.max_v_diff is not None else 'N/A',
                    self._extract_time(site_data.current_voltage_time),
                    f"{site_data.yesterday_max_soc:.1f}%" if site_data.yesterday_max_soc is not None else 'N/A'
                ]
                data_rows.append(row)
            
            # Combine headers and data
            all_rows = headers + data_rows
            
            # Update the data starting from row 2
            data_range = f"{self.sheet_name}!A2:K{len(all_rows) + 1}"
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=data_range,
                valueInputOption="RAW",
                body={"values": all_rows}
            ).execute()
            
            logger.info("Data successfully published to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error publishing to Google Sheets: {e}", exc_info=True)