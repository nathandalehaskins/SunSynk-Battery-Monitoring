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

## Technical Details

### Prerequisites
- Python 3.11+
- Google Sheets API credentials
- SunSynk API access
- Environment variables configuration

### Configuration Files
- Site configurations in YAML format
- Environment-specific settings
- Monitoring priorities per site
- API rate limits and retry settings

### Installation

1. Clone and setup environment:
```bash
git clone <repository-url>
cd sunsynk-monitor
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

2. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials:
# SUNSYNK_USERNAME=your_username
# SUNSYNK_PASSWORD=your_password
# GOOGLE_SHEETS_ID=your_sheet_id
```

3. Configure sites:
- Edit `config/development/sites.yaml` with your site details
- Each site requires:
  - Name
  - Site ID
  - Priority level
  - Monitoring preferences (SOC/voltage)

### Usage

Run the monitoring service:
```bash
python main.py
```

The service will:
- Validate all configured sites
- Cache site information
- Collect data every 15 minutes
- Update Google Sheets with latest readings
- Store raw and processed data locally

### Data Storage
- Raw API responses: `data/raw/`
- Processed analytics: `data/processed/`
- Site cache: `data/cache/`
- Application logs: `logs/`

## Monitoring Dashboard

The Google Sheets dashboard displays:
- Site Name and Inverter Serial Number
- Current and Lowest SOC values with timestamps
- Battery voltage readings and differentials
- Historical SOC data
- Site status indicators

## Error Handling
- Comprehensive logging system
- API