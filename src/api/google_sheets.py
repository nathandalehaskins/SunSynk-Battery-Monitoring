from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging
import os
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class GoogleSheetsPublisher:
    def __init__(self, config: Dict):
        self.config = config
        self.sheet_id = config['api']['google_sheets']['sheet_id']
        self.sheet_name = config['api']['google_sheets']['sheet_name']
        
        # Use the same file path as original implementation
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
        # Reference to original implementation:
        """python:STEP4_populate_to_sheet.py
        startLine: 8
        endLine: 11
        """
        if datetime_str:
            return datetime_str.split(" ")[1][:5]
        return None

    def _prepare_data(self, analysis_results: Dict) -> List[List]:
        """Prepare data for Google Sheets"""
        # Define headers
        headers = [
            'Site Name',
            'Inverter SN',
            'Lowest SOC',
            'Lowest Time',
            'Current SOC',
            'Current Time',
            'V-bat',
            'V-BMS',
            'V-Diff',
            'Voltage Time',
            'Yesterday Max SOC'
        ]
        
        # Start with headers
        values = [headers]
        
        # Add data rows
        for site_name, site_info in analysis_results.items():
            row = [
                site_name,
                site_info.inverter_sn,
                site_info.lowest_soc if site_info.lowest_soc != 'OFFLINE' else 'OFFLINE',
                self._extract_time(site_info.lowest_soc_time),
                site_info.current_soc if site_info.current_soc != 'OFFLINE' else 'OFFLINE',
                self._extract_time(site_info.current_soc_time),
                f"{site_info.current_v_bat:.2f}" if site_info.current_v_bat is not None else 'N/A',
                f"{site_info.current_vbms:.2f}" if site_info.current_vbms is not None else 'N/A',
                f"{site_info.max_v_diff:.2f}" if site_info.max_v_diff is not None else 'N/A',
                self._extract_time(site_info.current_voltage_time),
                f"{site_info.yesterday_max_soc:.1f}%" if site_info.yesterday_max_soc is not None else 'N/A'
            ]
            values.append(row)
        return values

    async def publish(self, analysis_results: Dict):
        """Publish data to Google Sheets"""
        try:
            # Clear the sheet first
            clear_range = f"{self.sheet_name}"
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.sheet_id,
                range=clear_range,
                body={}
            ).execute()

            values = self._prepare_data(analysis_results)
            body = {'values': values}
            
            result = self.service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=f"{self.sheet_name}!A1",
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"Updated {result.get('updatedCells')} cells")
        except Exception as e:
            logger.error(f"Error publishing to Google Sheets: {e}")