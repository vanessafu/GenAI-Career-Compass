"""
Configuration Management for Career Compass

Loading Priority (highest to lowest):
1. Environment Variables (.env)
2. YAML (config/default.config.yaml)

Usage:
  from modules.shared.config import get_config
  config = get_config()
  value = config.get("KEY", default=None)
  required = config.require("REQUIRED_KEY")
"""

import os
import yaml
from typing import Any, Dict
from functools import lru_cache


class Config:
    """Configuration manager supporting YAML + environment variables."""
    
    def __init__(self):
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load config from YAML + environment variables (env vars override)."""
        config = {}
        
        # Load YAML
        config_path = "config/default.config.yaml"
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                config.update(yaml.safe_load(f) or {})
        
        # Override with environment variables
        for key in os.environ:
            if key.startswith(('LLM_', 'ESCO_', 'ONET_', 'VECTOR_', 'DATABASE_', 'REDIS_', 'API_')):
                config[key] = os.environ[key]
        
        return config
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get config value or default if not found."""
        return self.config_data.get(key, default)
    
    def require(self, key: str) -> Any:
        """Get required config value. Raises KeyError if missing."""
        if key not in self.config_data:
            raise KeyError(f"Missing required config: {key}")
        return self.config_data[key]


@lru_cache(maxsize=1)
def get_config() -> Config:
    """Get global config instance (cached singleton)."""
    return Config()
