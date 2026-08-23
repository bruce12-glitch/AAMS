"""
Configuration loader for FacePass FabLab.
Loads config.yaml and environment variables.
Implements §21 Configuration Specification.
"""

import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the base directory (where config.yaml is located)
BASE_DIR = Path(__file__).parent.parent

def load_config():
    """
    Load configuration from config.yaml and merge with environment variables.
    Returns a dictionary with all configuration values.
    """
    config_path = BASE_DIR / "config.yaml"
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # Override with environment variables where applicable
    if os.getenv('TELEGRAM_BOT_TOKEN'):
        config['alerts']['telegram_bot_token'] = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if os.getenv('TELEGRAM_CHAT_ID'):
        config['alerts']['telegram_chat_id'] = os.getenv('TELEGRAM_CHAT_ID')
    
    if os.getenv('QR_SECRET_KEY'):
        config['security']['qr_secret_key'] = os.getenv('QR_SECRET_KEY')
    
    if os.getenv('API_ADMIN_PASSWORD'):
        config['security']['api_admin_password'] = os.getenv('API_ADMIN_PASSWORD')
    
    if os.getenv('DATABASE_PATH'):
        config['database']['path'] = os.getenv('DATABASE_PATH')
    
    return config

# Global config instance
_config = None

def get_config():
    """
    Get the global configuration instance.
    Loads config on first call.
    """
    global _config
    if _config is None:
        _config = load_config()
    return _config

def get_database_path():
    """Get the absolute path to the database file."""
    config = get_config()
    db_path = config['database']['path']
    if not os.path.isabs(db_path):
        return BASE_DIR / db_path
    return db_path

def get_telegram_config():
    """Get Telegram bot configuration."""
    config = get_config()
    return {
        'enabled': config['alerts'].get('telegram_enabled', False),
        'bot_token': config['alerts'].get('telegram_bot_token', ''),
        'chat_id': config['alerts'].get('telegram_chat_id', ''),
        'send_photo': config['alerts'].get('send_photo', True)
    }

def get_face_config():
    """Get face recognition configuration."""
    config = get_config()
    return config['face']

def get_camera_config():
    """Get camera configuration."""
    config = get_config()
    return config['camera']

def get_occupancy_config():
    """Get occupancy tracking configuration."""
    config = get_config()
    return config['occupancy']

def get_security_config():
    """Get security configuration."""
    config = get_config()
    return config['security']
