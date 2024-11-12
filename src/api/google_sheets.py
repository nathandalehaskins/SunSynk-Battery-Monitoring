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
            # Get current timestamp
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Define headers for all columns including the timestamp
            headers = [
                ["Last Updated:", current_time],
                ["Site Name", "Current SOC", "Current SOC Time", "Lowest SOC", "Lowest SOC Time", 
                 "V-bat", "V-BMS", "Voltage Diff", "Yesterday Max SOC", "Status", "Yesterday Max SOC"]
            ]
            
            # Create data rows
            data_rows = []
            for site_name, site_data in data.items():
                status = 'OFFLINE' if site_data.current_soc == 'OFFLINE' else 'ONLINE'
                row = [
                    site_name,
                    site_data.current_soc,
                    site_data.current_soc_time,
                    site_data.lowest_soc,
                    site_data.lowest_soc_time,
                    site_data.current_v_bat,
                    site_data.current_vbms,
                    site_data.max_v_diff,
                    site_data.yesterday_max_soc,
                    status,
                    f"{site_data.yesterday_max_soc}%"  # Add percentage for last column
                ]
                data_rows.append(row)
            
            # Combine headers and data
            all_rows = headers + data_rows
            
            # Clear and update the entire range at once
            range_name = f"{self.sheet_name}!A1:K{len(all_rows)}"
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()
            
            self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": all_rows}
            ).execute()
            
            logger.info("Data successfully published to Google Sheets")
            
        except Exception as e:
            logger.error(f"Error publishing to Google Sheets: {e}", exc_info=True)