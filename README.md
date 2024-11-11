# SunSynk Battery Monitor

A Python-based monitoring system for SunSynk inverters that tracks battery health and performance metrics across multiple solar installations. Built for automated data collection and real-time monitoring of battery voltage differentials and state of charge.

## Overview

This application monitors multiple SunSynk inverter sites, collecting critical battery metrics every 15 minutes and publishing them to Google Sheets for analysis. It's specifically designed to track battery voltage differentials and SOC levels to ensure optimal battery performance and early detection of potential issues.

## Key Features

### Battery Monitoring
- Real-time battery voltage tracking (V-bat and BMS voltage)
- Voltage differential calculations
- State of Charge (SOC) monitoring
- Historical SOC tracking (previous day's maximum)
- Offline status detection

### Data Collection & Analysis
- 15-minute automated data collection intervals
- Daily site refresh at 5 AM
- Parallel data fetching for improved performance
- Cached site validation to reduce API load
- Configurable retry mechanisms for API failures

### Reporting
- Automated Google Sheets updates with:
  - Current and lowest SOC levels with timestamps
  - Battery voltage readings (V-bat, V-BMS, Voltage differential)
  - Yesterday's maximum SOC percentage
  - Site status (online/offline)

## Installation

### Prerequisites
- Python 3.11+
- Google Sheets API credentials
- SunSynk API access
- Environment variables configuration

### Setup Steps

1. Clone the repository:
```bash
git clone https://github.com/nathandalehaskins/SunSynk-Battery-Monitoring.git
cd SunSynk-Battery-Monitoring
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up configuration:
```bash
# Copy example configuration files
cp .env.example .env
cp config/development/config.example.yaml config/development/config.yaml
cp config/development/sites.example.yaml config/development/sites.yaml

# Edit the configuration files with your settings
```

5. Configure Google Sheets:
- Place your Google Sheets API credentials in `credentials/site-performance-info-credentials.json`
- Update the sheet ID in your `.env` file

6. Configure sites:
- Edit `config/development/sites.yaml` with your site details
- Each site requires:
  - Name
  - Site ID
  - Priority level
  - Monitoring preferences (SOC/voltage)

## Usage

Run the monitoring service:
```bash
python main.py
```

The service will:
- Validate configured sites
- Cache site information
- Collect data every 15 minutes
- Update Google Sheets with latest readings
- Store raw and processed data locally

## Directory Structure
```
SunSynk-Battery-Monitoring/
├── src/
│   ├── api/              # API clients
│   ├── core/             # Core functionality
│   ├── services/         # Service layer
│   └── validators/       # Data validation
├── config/
│   └── development/      # Configuration files
├── data/
│   ├── cache/           # Cached site data
│   ├── raw/             # Raw API responses
│   └── processed/       # Analyzed data
├── logs/                # Application logs
└── credentials/         # API credentials
```

## Google Sheets Dashboard

The monitoring dashboard displays:
- Site Name and Inverter Serial Number
- Current and Lowest SOC values with timestamps
- Battery voltage readings and differentials
- Historical SOC data
- Site status indicators

## Error Handling
- Comprehensive logging system
- API failure recovery
- Data validation checks
- Offline site detection
- Rate limit protection

## License
MIT License

## Google Sheets Integration Setup

### 1. Create Google Cloud Project
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google Sheets API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google Sheets API"
   - Click "Enable"

### 2. Create Service Account Credentials
1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "Service Account"
3. Fill in service account details:
   - Name: "sunsynk-monitor"
   - Role: "Editor"
4. Click "Done"
5. Under "Service Accounts", click on the newly created account
6. Go to "Keys" tab
7. Click "Add Key" > "Create New Key"
8. Choose JSON format
9. Download the credentials file
10. Place the downloaded file in `credentials/site-performance-info-credentials.json`

### 3. Set Up Google Sheet
1. Create a new Google Sheet
2. Share the sheet with the service account email (found in your credentials JSON)
   - Give "Editor" permissions
3. Copy the Sheet ID from the URL:
   ```
   https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit#gid=0
   ```
4. Add the Sheet ID to your `.env` file:
   ```
   GOOGLE_SHEETS_ID=your_sheet_id_here
   ```

### 4. Sheet Structure
The application expects the following columns in your Google Sheet:

| Site Name | Inverter SN | Lowest SOC | Lowest Time | Current SOC | Current Time | V-bat | V-BMS | V-Diff | Voltage Time | Yesterday Max SOC |
|-----------|-------------|------------|-------------|-------------|--------------|-------|-------|---------|--------------|------------------|

### Example Credentials File Structure
Your `credentials/site-performance-info-credentials.json` should look like this:
```
json
{
"type": "service_account",
"project_id": "your-project-id",
"private_key_id": "your-private-key-id",
"private_key": "your-private-key",
"client_email": "your-service-account@your-project.iam.gserviceaccount.com",
"client_id": "your-client-id",
"auth_uri": "https://accounts.google.com/o/oauth2/auth",
"token_uri": "https://oauth2.googleapis.com/token",
"auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
"client_x509_cert_url": "your-cert-url"
}
```
### Troubleshooting
Common issues and solutions:
1. "Google Sheets API has not been enabled":
   - Ensure you've enabled the API in Google Cloud Console
2. "Permission denied":
   - Check if the service account email has editor access to the sheet
3. "Invalid credentials":
   - Verify the credentials file is correctly placed and formatted
4. "Sheet not found":
   - Double-check the Sheet ID in your `.env` file
