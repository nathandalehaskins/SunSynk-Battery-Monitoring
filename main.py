import asyncio
import logging
import os
from src.services.monitoring import MonitoringService
import yaml
from dotenv import load_dotenv

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/app.log'),
            logging.StreamHandler()
        ]
    )

def load_config():
    # Load environment variables from .env file
    load_dotenv()
    
    env = os.getenv('ENVIRONMENT', 'development')
    config_path = f'config/{env}/config.yaml'
    
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    # Replace environment variables in config
    config['api']['sunsynk']['username'] = os.getenv('SUNSYNK_USERNAME')
    config['api']['sunsynk']['password'] = os.getenv('SUNSYNK_PASSWORD')
    config['api']['google_sheets']['sheet_id'] = os.getenv('GOOGLE_SHEETS_ID')
    
    if not all([
        config['api']['sunsynk']['username'],
        config['api']['sunsynk']['password'],
        config['api']['google_sheets']['sheet_id']
    ]):
        raise ValueError("Missing required environment variables")
    
    return config

async def main():
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        config = load_config()
        service = MonitoringService(config)
        await service.run()
    except Exception as e:
        logger.error(f"Fatal error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())