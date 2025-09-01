"""
Configuration Manager
Centralized configuration loading and management for all agents and components
"""
import os
import yaml
import json
import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from dotenv import load_dotenv
import re


class Environment(str, Enum):
    """Environment types"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    database: str = "regulations_db"
    username: str = "postgres"
    password: str = ""
    ssl_mode: str = "prefer"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600


@dataclass
class RedisConfig:
    """Redis configuration"""
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    ssl: bool = False
    socket_timeout: int = 5
    socket_connect_timeout: int = 5
    socket_keepalive: bool = True
    health_check_interval: int = 30
    max_connections: int = 100
    retry_on_timeout: bool = True


@dataclass
class OpenAIConfig:
    """OpenAI API configuration"""
    api_key: Optional[str] = None
    organization: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    default_model: str = "gpt-4o"
    vision_model: str = "gpt-4o"
    embedding_model: str = "text-embedding-3-large"
    max_tokens: int = 4000
    temperature: float = 0.1
    timeout: int = 60
    max_retries: int = 3
    request_delay: float = 0.1
    rate_limit_rpm: int = 3000  # requests per minute
    rate_limit_tpm: int = 150000  # tokens per minute
    
    # SDK-specific settings
    tracing_enabled: bool = True
    debug_mode: bool = False
    session_timeout: int = 3600  # 1 hour
    auto_handoff_enabled: bool = True
    guardrails_enabled: bool = True


@dataclass
class AgentConfig:
    """Agent configuration"""
    enabled: bool = True
    max_concurrent_jobs: int = 5
    request_delay: float = 1.0
    timeout: int = 30
    max_retries: int = 3
    user_agent: str = "RegulationScraper/1.0"
    batch_size: int = 10
    rate_limit: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheConfig:
    """Cache configuration"""
    redis_enabled: bool = True
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    local_cache_size_mb: int = 256
    file_cache_dir: str = "./cache"
    file_cache_threshold: int = 1048576  # 1MB
    compression_enabled: bool = True
    default_ttl_hours: int = 24


@dataclass
class OptimizationConfig:
    """Performance optimization configuration"""
    enabled: bool = True
    max_concurrent_requests: int = 20
    max_parallel_extractions: int = 5
    batch_processing_enabled: bool = True
    request_deduplication: bool = True
    smart_retry_enabled: bool = True
    cache_aggressive: bool = True


@dataclass
class ExtractionConfig:
    """Extraction configuration"""
    max_document_size: int = 10_000_000  # 10MB
    max_documents_per_job: int = 1000
    pdf_ocr_enabled: bool = True
    vision_processing_enabled: bool = True
    text_quality_threshold: float = 0.6
    confidence_threshold: float = 0.7
    languages: List[str] = field(default_factory=lambda: ["en"])


@dataclass
class APIConfig:
    """API configuration"""
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 4
    access_log: bool = True
    cors_enabled: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    rate_limiting: Dict[str, Any] = field(default_factory=dict)
    auth_enabled: bool = False
    auth_token: Optional[str] = None


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: str = "logs/regulation_scraper.log"
    file_max_size: str = "10MB"
    file_backup_count: int = 5
    console_enabled: bool = True
    console_level: str = "INFO"


@dataclass
class MonitoringConfig:
    """Monitoring configuration"""
    enabled: bool = True
    health_check_interval: int = 60
    metrics_enabled: bool = True
    metrics_port: int = 9090
    alert_enabled: bool = True
    alert_thresholds: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityConfig:
    """Security configuration"""
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    api_key_required: bool = False
    rate_limiting_enabled: bool = True
    max_requests_per_minute: int = 100
    ip_whitelist: List[str] = field(default_factory=list)
    ip_blacklist: List[str] = field(default_factory=list)


@dataclass
class Config:
    """Main configuration class"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    
    # Component configurations
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)
    api: APIConfig = field(default_factory=APIConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    extraction: ExtractionConfig = field(default_factory=ExtractionConfig)
    
    # Agent configurations
    agents: Dict[str, AgentConfig] = field(default_factory=dict)
    
    # Custom settings
    custom: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Central configuration manager"""
    
    def __init__(self, config_dir: Optional[str] = None, environment: Optional[str] = None):
        self.logger = logging.getLogger(__name__)
        
        # Set configuration directory
        if config_dir:
            self.config_dir = Path(config_dir)
        else:
            # Default to config directory relative to project root
            self.config_dir = Path(__file__).parent.parent.parent / "config"
        
        # Load environment variables
        load_dotenv()
        
        # Determine environment
        self.environment = Environment(
            environment or 
            os.getenv("ENVIRONMENT", "development").lower()
        )
        
        self._config: Optional[Config] = None
        self._load_config()
    
    def _load_config(self):
        """Load configuration from files and environment variables"""
        try:
            # Start with default configuration
            config_data = {}
            
            # Load base configuration
            base_config_path = self.config_dir / "base.yaml"
            if base_config_path.exists():
                config_data.update(self._load_yaml_file(base_config_path))
            
            # Load environment-specific configuration
            env_config_path = self.config_dir / "environments" / f"{self.environment.value}.yaml"
            if env_config_path.exists():
                env_config = self._load_yaml_file(env_config_path)
                config_data = self._deep_merge(config_data, env_config)
            
            # Load local overrides (not in version control)
            local_config_path = self.config_dir / "local.yaml"
            if local_config_path.exists():
                local_config = self._load_yaml_file(local_config_path)
                config_data = self._deep_merge(config_data, local_config)
            
            # Apply environment variable overrides
            config_data = self._apply_env_overrides(config_data)
            
            # Create Config object
            self._config = self._create_config_object(config_data)
            
            self.logger.info(f"Configuration loaded for environment: {self.environment.value}")
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Fall back to default configuration
            self._config = Config(environment=self.environment)
    
    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                return data or {}
        except Exception as e:
            self.logger.warning(f"Failed to load config file {file_path}: {e}")
            return {}
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries"""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        
        # Database overrides
        if os.getenv("DATABASE_URL"):
            db_url = os.getenv("DATABASE_URL")
            # Parse DATABASE_URL (format: postgresql://user:pass@host:port/db)
            db_config = self._parse_database_url(db_url)
            if db_config:
                config_data.setdefault("database", {}).update(db_config)
        
        # Individual database settings
        env_mappings = {
            "DB_HOST": ("database", "host"),
            "DB_PORT": ("database", "port"),
            "DB_NAME": ("database", "database"),
            "DB_USER": ("database", "username"),
            "DB_PASSWORD": ("database", "password"),
            "DB_SSL_MODE": ("database", "ssl_mode"),
            
            # Redis overrides
            "REDIS_URL": ("redis", "url"),
            "REDIS_HOST": ("redis", "host"),
            "REDIS_PORT": ("redis", "port"),
            "REDIS_DB": ("redis", "db"),
            "REDIS_PASSWORD": ("redis", "password"),
            
            # OpenAI overrides
            "OPENAI_API_KEY": ("openai", "api_key"),
            "OPENAI_ORGANIZATION": ("openai", "organization"),
            "OPENAI_BASE_URL": ("openai", "base_url"),
            "OPENAI_DEFAULT_MODEL": ("openai", "default_model"),
            "OPENAI_VISION_MODEL": ("openai", "vision_model"),
            "OPENAI_MAX_TOKENS": ("openai", "max_tokens"),
            "OPENAI_TEMPERATURE": ("openai", "temperature"),
            "OPENAI_TIMEOUT": ("openai", "timeout"),
            "OPENAI_MAX_RETRIES": ("openai", "max_retries"),
            
            # API overrides
            "API_HOST": ("api", "host"),
            "API_PORT": ("api", "port"),
            "API_DEBUG": ("api", "debug"),
            "API_WORKERS": ("api", "workers"),
            
            # Security overrides
            "SECRET_KEY": ("security", "encryption_key"),
            "API_KEY": ("security", "api_key"),
            
            # General overrides
            "DEBUG": ("debug",),
            "LOG_LEVEL": ("logging", "level"),
        }
        
        for env_var, config_path in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Type conversion
                value = self._convert_env_value(value)
                
                # Set nested configuration
                current = config_data
                for key in config_path[:-1]:
                    current = current.setdefault(key, {})
                current[config_path[-1]] = value
        
        return config_data
    
    def _parse_database_url(self, db_url: str) -> Optional[Dict[str, Any]]:
        """Parse DATABASE_URL into components"""
        try:
            # Example: postgresql://user:pass@host:port/db
            pattern = r'postgresql://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)'
            match = re.match(pattern, db_url)
            
            if match:
                username, password, host, port, database = match.groups()
                return {
                    "host": host,
                    "port": int(port),
                    "database": database,
                    "username": username,
                    "password": password
                }
        except Exception as e:
            self.logger.warning(f"Failed to parse DATABASE_URL: {e}")
        
        return None
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable string to appropriate type"""
        # Boolean conversion
        if value.lower() in ('true', '1', 'yes', 'on'):
            return True
        if value.lower() in ('false', '0', 'no', 'off'):
            return False
        
        # Integer conversion
        if value.isdigit():
            return int(value)
        
        # Float conversion
        try:
            if '.' in value:
                return float(value)
        except ValueError:
            pass
        
        # JSON conversion
        if value.startswith('{') or value.startswith('['):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                pass
        
        # Return as string
        return value
    
    def _create_config_object(self, config_data: Dict[str, Any]) -> Config:
        """Create Config object from dictionary"""
        try:
            # Create component configurations
            database = DatabaseConfig(**config_data.get("database", {}))
            redis = RedisConfig(**config_data.get("redis", {}))
            openai = OpenAIConfig(**config_data.get("openai", {}))
            cache = CacheConfig(**config_data.get("cache", {}))
            optimization = OptimizationConfig(**config_data.get("optimization", {}))
            api = APIConfig(**config_data.get("api", {}))
            logging_config = LoggingConfig(**config_data.get("logging", {}))
            monitoring = MonitoringConfig(**config_data.get("monitoring", {}))
            security = SecurityConfig(**config_data.get("security", {}))
            extraction = ExtractionConfig(**config_data.get("extraction", {}))
            
            # Create agent configurations
            agents = {}
            agent_configs = config_data.get("agents", {})
            for agent_name, agent_data in agent_configs.items():
                agents[agent_name] = AgentConfig(**agent_data)
            
            # Create main config
            return Config(
                environment=self.environment,
                debug=config_data.get("debug", False),
                database=database,
                redis=redis,
                openai=openai,
                cache=cache,
                optimization=optimization,
                api=api,
                logging=logging_config,
                monitoring=monitoring,
                security=security,
                extraction=extraction,
                agents=agents,
                custom=config_data.get("custom", {})
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create config object: {e}")
            return Config(environment=self.environment)
    
    @property
    def config(self) -> Config:
        """Get current configuration"""
        if self._config is None:
            self._load_config()
        return self._config
    
    def reload(self):
        """Reload configuration from files"""
        self._load_config()
        self.logger.info("Configuration reloaded")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key (supports dot notation)"""
        try:
            keys = key.split('.')
            value = self.config
            
            for k in keys:
                if hasattr(value, k):
                    value = getattr(value, k)
                elif isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return value
            
        except Exception:
            return default
    
    def set(self, key: str, value: Any):
        """Set configuration value by key (supports dot notation)"""
        try:
            keys = key.split('.')
            target = self.config
            
            for k in keys[:-1]:
                if hasattr(target, k):
                    target = getattr(target, k)
                elif isinstance(target, dict):
                    target = target.setdefault(k, {})
                else:
                    return False
            
            final_key = keys[-1]
            if hasattr(target, final_key):
                setattr(target, final_key, value)
            elif isinstance(target, dict):
                target[final_key] = value
            else:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to set config value {key}: {e}")
            return False
    
    def get_database_url(self) -> str:
        """Get database connection URL"""
        db = self.config.database
        return f"postgresql://{db.username}:{db.password}@{db.host}:{db.port}/{db.database}"
    
    def get_redis_url(self) -> str:
        """Get Redis connection URL"""
        redis = self.config.redis
        auth = f":{redis.password}@" if redis.password else ""
        return f"redis://{auth}{redis.host}:{redis.port}/{redis.db}"
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of issues"""
        issues = []
        
        try:
            # Validate database configuration
            if not self.config.database.host:
                issues.append("Database host is required")
            if not self.config.database.database:
                issues.append("Database name is required")
            if not self.config.database.username:
                issues.append("Database username is required")
            
            # Validate Redis configuration
            if not self.config.redis.host:
                issues.append("Redis host is required")
            
            # Validate API configuration
            if self.config.api.port <= 0 or self.config.api.port > 65535:
                issues.append("Invalid API port number")
            
            # Validate logging configuration
            valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if self.config.logging.level.upper() not in valid_log_levels:
                issues.append(f"Invalid log level: {self.config.logging.level}")
            
            # Validate agent configurations
            for agent_name, agent_config in self.config.agents.items():
                if agent_config.max_concurrent_jobs <= 0:
                    issues.append(f"Invalid max_concurrent_jobs for agent {agent_name}")
                if agent_config.timeout <= 0:
                    issues.append(f"Invalid timeout for agent {agent_name}")
            
        except Exception as e:
            issues.append(f"Configuration validation error: {e}")
        
        return issues
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        def _convert_to_dict(obj):
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    result[key] = _convert_to_dict(value)
                return result
            elif isinstance(obj, dict):
                return {k: _convert_to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [_convert_to_dict(item) for item in obj]
            elif isinstance(obj, Enum):
                return obj.value
            else:
                return obj
        
        return _convert_to_dict(self.config)


# Global configuration manager instance
_config_manager: Optional[ConfigManager] = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager instance"""
    global _config_manager
    
    if _config_manager is None:
        _config_manager = ConfigManager()
    
    return _config_manager


def get_config() -> Config:
    """Get current configuration"""
    return get_config_manager().config


def reload_config():
    """Reload configuration from files"""
    global _config_manager
    if _config_manager:
        _config_manager.reload()


# Convenience functions
def get_database_url() -> str:
    """Get database connection URL"""
    return get_config_manager().get_database_url()


def get_redis_url() -> str:
    """Get Redis connection URL"""
    return get_config_manager().get_redis_url()


def is_debug() -> bool:
    """Check if debug mode is enabled"""
    return get_config().debug


def is_production() -> bool:
    """Check if running in production environment"""
    return get_config().environment == Environment.PRODUCTION