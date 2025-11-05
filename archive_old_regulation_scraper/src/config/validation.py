"""
Configuration validation utilities
Validates configuration settings for correctness and completeness
"""
import re
import socket
from typing import List, Dict, Any, Tuple, Optional
from urllib.parse import urlparse
from pathlib import Path
import logging

from .config_manager import Config, Environment


class ConfigValidator:
    """Validates configuration settings"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.errors: List[str] = []
        self.warnings: List[str] = []
    
    def validate_all(self) -> Tuple[List[str], List[str]]:
        """
        Validate all configuration settings
        
        Returns:
            Tuple of (errors, warnings)
        """
        self.errors.clear()
        self.warnings.clear()
        
        # Validate all components
        self._validate_database()
        self._validate_redis()
        self._validate_api()
        self._validate_logging()
        self._validate_monitoring()
        self._validate_security()
        self._validate_extraction()
        self._validate_agents()
        self._validate_environment_specific()
        
        return self.errors.copy(), self.warnings.copy()
    
    def _validate_database(self):
        """Validate database configuration"""
        db = self.config.database
        
        # Required fields
        if not db.host:
            self.errors.append("Database host is required")
        elif not self._is_valid_hostname(db.host):
            self.errors.append(f"Invalid database host: {db.host}")
        
        if not db.database:
            self.errors.append("Database name is required")
        elif not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', db.database):
            self.errors.append(f"Invalid database name: {db.database}")
        
        if not db.username:
            self.errors.append("Database username is required")
        
        # Port validation
        if not self._is_valid_port(db.port):
            self.errors.append(f"Invalid database port: {db.port}")
        
        # Pool settings validation
        if db.pool_size <= 0:
            self.errors.append("Database pool_size must be positive")
        elif db.pool_size > 100:
            self.warnings.append("Database pool_size is very high, consider reducing")
        
        if db.max_overflow < 0:
            self.errors.append("Database max_overflow cannot be negative")
        elif db.max_overflow > db.pool_size * 2:
            self.warnings.append("Database max_overflow is much larger than pool_size")
        
        if db.pool_timeout <= 0:
            self.errors.append("Database pool_timeout must be positive")
        
        # SSL mode validation
        valid_ssl_modes = ['disable', 'allow', 'prefer', 'require', 'verify-ca', 'verify-full']
        if db.ssl_mode not in valid_ssl_modes:
            self.errors.append(f"Invalid SSL mode: {db.ssl_mode}")
        
        # Production-specific validations
        if self.config.environment == Environment.PRODUCTION:
            if not db.password:
                self.warnings.append("Database password is empty in production")
            if db.ssl_mode in ['disable', 'allow']:
                self.warnings.append("Consider using stricter SSL mode in production")
    
    def _validate_redis(self):
        """Validate Redis configuration"""
        redis = self.config.redis
        
        # Required fields
        if not redis.host:
            self.errors.append("Redis host is required")
        elif not self._is_valid_hostname(redis.host):
            self.errors.append(f"Invalid Redis host: {redis.host}")
        
        # Port validation
        if not self._is_valid_port(redis.port):
            self.errors.append(f"Invalid Redis port: {redis.port}")
        
        # Database number validation
        if redis.db < 0 or redis.db > 15:
            self.errors.append("Redis database number must be between 0-15")
        
        # Timeout validation
        if redis.socket_timeout <= 0:
            self.errors.append("Redis socket_timeout must be positive")
        
        if redis.socket_connect_timeout <= 0:
            self.errors.append("Redis socket_connect_timeout must be positive")
        
        if redis.health_check_interval <= 0:
            self.errors.append("Redis health_check_interval must be positive")
        
        # Connection pool validation
        if redis.max_connections <= 0:
            self.errors.append("Redis max_connections must be positive")
        elif redis.max_connections > 1000:
            self.warnings.append("Redis max_connections is very high")
        
        # Production-specific validations
        if self.config.environment == Environment.PRODUCTION:
            if not redis.password:
                self.warnings.append("Redis password is not set in production")
            if not redis.ssl:
                self.warnings.append("Consider enabling SSL for Redis in production")
    
    def _validate_api(self):
        """Validate API configuration"""
        api = self.config.api
        
        # Host validation
        if not api.host:
            self.errors.append("API host is required")
        elif not self._is_valid_ip_or_hostname(api.host):
            self.errors.append(f"Invalid API host: {api.host}")
        
        # Port validation
        if not self._is_valid_port(api.port):
            self.errors.append(f"Invalid API port: {api.port}")
        
        # Worker validation
        if api.workers <= 0:
            self.errors.append("API workers must be positive")
        elif api.workers > 20:
            self.warnings.append("Very high number of API workers")
        
        # CORS validation
        if api.cors_enabled and api.cors_origins:
            for origin in api.cors_origins:
                if origin != "*" and not self._is_valid_url(origin):
                    self.warnings.append(f"Invalid CORS origin: {origin}")
        
        # Rate limiting validation
        if api.rate_limiting and isinstance(api.rate_limiting, dict):
            if api.rate_limiting.get('enabled', False):
                rpm = api.rate_limiting.get('requests_per_minute', 0)
                if rpm <= 0:
                    self.errors.append("Rate limiting requests_per_minute must be positive")
        
        # Production-specific validations
        if self.config.environment == Environment.PRODUCTION:
            if api.debug:
                self.warnings.append("API debug mode is enabled in production")
            if api.reload:
                self.warnings.append("API reload is enabled in production")
            if "*" in api.cors_origins:
                self.warnings.append("CORS allows all origins in production")
            if not api.auth_enabled:
                self.warnings.append("API authentication is disabled in production")
    
    def _validate_logging(self):
        """Validate logging configuration"""
        log = self.config.logging
        
        # Log level validation
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if log.level.upper() not in valid_levels:
            self.errors.append(f"Invalid log level: {log.level}")
        
        if log.console_level.upper() not in valid_levels:
            self.errors.append(f"Invalid console log level: {log.console_level}")
        
        # File path validation
        if log.file_enabled:
            if not log.file_path:
                self.errors.append("Log file path is required when file logging is enabled")
            else:
                log_path = Path(log.file_path)
                try:
                    # Check if directory exists or can be created
                    log_path.parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.errors.append(f"Cannot create log directory: {e}")
        
        # File size validation
        if log.file_enabled and log.file_max_size:
            if not re.match(r'^\d+[KMGT]?B$', log.file_max_size.upper()):
                self.errors.append(f"Invalid log file max size format: {log.file_max_size}")
        
        # Backup count validation
        if log.file_backup_count < 0:
            self.errors.append("Log file backup count cannot be negative")
        elif log.file_backup_count > 50:
            self.warnings.append("Very high log file backup count")
    
    def _validate_monitoring(self):
        """Validate monitoring configuration"""
        mon = self.config.monitoring
        
        # Health check interval validation
        if mon.health_check_interval <= 0:
            self.errors.append("Health check interval must be positive")
        elif mon.health_check_interval < 10:
            self.warnings.append("Very frequent health checks may impact performance")
        
        # Metrics port validation
        if mon.metrics_enabled:
            if not self._is_valid_port(mon.metrics_port):
                self.errors.append(f"Invalid metrics port: {mon.metrics_port}")
            elif mon.metrics_port == self.config.api.port:
                self.warnings.append("Metrics port conflicts with API port")
        
        # Alert thresholds validation
        if mon.alert_thresholds:
            if 'memory_usage_mb' in mon.alert_thresholds:
                memory_threshold = mon.alert_thresholds['memory_usage_mb']
                if memory_threshold <= 0:
                    self.errors.append("Memory usage threshold must be positive")
            
            if 'cpu_usage_percent' in mon.alert_thresholds:
                cpu_threshold = mon.alert_thresholds['cpu_usage_percent']
                if cpu_threshold <= 0 or cpu_threshold > 100:
                    self.errors.append("CPU usage threshold must be between 0-100")
            
            if 'error_rate_percent' in mon.alert_thresholds:
                error_threshold = mon.alert_thresholds['error_rate_percent']
                if error_threshold <= 0 or error_threshold > 100:
                    self.errors.append("Error rate threshold must be between 0-100")
    
    def _validate_security(self):
        """Validate security configuration"""
        sec = self.config.security
        
        # Encryption validation
        if sec.encryption_enabled and not sec.encryption_key:
            self.errors.append("Encryption key is required when encryption is enabled")
        elif sec.encryption_key and len(sec.encryption_key) < 32:
            self.warnings.append("Encryption key is shorter than recommended (32 characters)")
        
        # Rate limiting validation
        if sec.rate_limiting_enabled:
            if sec.max_requests_per_minute <= 0:
                self.errors.append("Max requests per minute must be positive")
        
        # IP list validation
        for ip in sec.ip_whitelist:
            if not self._is_valid_ip_or_cidr(ip):
                self.warnings.append(f"Invalid IP in whitelist: {ip}")
        
        for ip in sec.ip_blacklist:
            if not self._is_valid_ip_or_cidr(ip):
                self.warnings.append(f"Invalid IP in blacklist: {ip}")
        
        # Production-specific validations
        if self.config.environment == Environment.PRODUCTION:
            if not sec.encryption_enabled:
                self.warnings.append("Encryption is disabled in production")
            if not sec.api_key_required:
                self.warnings.append("API key authentication is disabled in production")
            if not sec.rate_limiting_enabled:
                self.warnings.append("Rate limiting is disabled in production")
    
    def _validate_extraction(self):
        """Validate extraction configuration"""
        ext = self.config.extraction
        
        # Document size validation
        if ext.max_document_size <= 0:
            self.errors.append("Max document size must be positive")
        elif ext.max_document_size > 100 * 1024 * 1024:  # 100MB
            self.warnings.append("Very large max document size may cause memory issues")
        
        # Documents per job validation
        if ext.max_documents_per_job <= 0:
            self.errors.append("Max documents per job must be positive")
        elif ext.max_documents_per_job > 10000:
            self.warnings.append("Very high max documents per job may cause performance issues")
        
        # Threshold validation
        if not 0.0 <= ext.text_quality_threshold <= 1.0:
            self.errors.append("Text quality threshold must be between 0.0 and 1.0")
        
        if not 0.0 <= ext.confidence_threshold <= 1.0:
            self.errors.append("Confidence threshold must be between 0.0 and 1.0")
        
        # Language validation
        if not ext.languages:
            self.errors.append("At least one language must be specified")
        else:
            for lang in ext.languages:
                if not re.match(r'^[a-z]{2,3}$', lang):
                    self.warnings.append(f"Invalid language code: {lang}")
    
    def _validate_agents(self):
        """Validate agent configurations"""
        for agent_name, agent_config in self.config.agents.items():
            self._validate_single_agent(agent_name, agent_config)
    
    def _validate_single_agent(self, name: str, config):
        """Validate single agent configuration"""
        # Concurrent jobs validation
        if config.max_concurrent_jobs <= 0:
            self.errors.append(f"Agent {name}: max_concurrent_jobs must be positive")
        elif config.max_concurrent_jobs > 20:
            self.warnings.append(f"Agent {name}: very high max_concurrent_jobs")
        
        # Request delay validation
        if config.request_delay < 0:
            self.errors.append(f"Agent {name}: request_delay cannot be negative")
        elif config.request_delay > 10:
            self.warnings.append(f"Agent {name}: very high request_delay")
        
        # Timeout validation
        if config.timeout <= 0:
            self.errors.append(f"Agent {name}: timeout must be positive")
        elif config.timeout > 3600:  # 1 hour
            self.warnings.append(f"Agent {name}: very high timeout")
        
        # Retry validation
        if config.max_retries < 0:
            self.errors.append(f"Agent {name}: max_retries cannot be negative")
        elif config.max_retries > 10:
            self.warnings.append(f"Agent {name}: very high max_retries")
        
        # Batch size validation
        if config.batch_size <= 0:
            self.errors.append(f"Agent {name}: batch_size must be positive")
        elif config.batch_size > 100:
            self.warnings.append(f"Agent {name}: very high batch_size")
        
        # User agent validation
        if not config.user_agent:
            self.warnings.append(f"Agent {name}: user_agent is empty")
        elif len(config.user_agent) > 200:
            self.warnings.append(f"Agent {name}: user_agent is very long")
        
        # Rate limit validation
        if config.rate_limit and isinstance(config.rate_limit, dict):
            if config.rate_limit.get('enabled', False):
                max_per_min = config.rate_limit.get('max_per_minute', 0)
                if max_per_min <= 0:
                    self.errors.append(f"Agent {name}: rate limit max_per_minute must be positive")
    
    def _validate_environment_specific(self):
        """Validate environment-specific settings"""
        env = self.config.environment
        
        if env == Environment.PRODUCTION:
            # Production-specific validations
            if self.config.debug:
                self.warnings.append("Debug mode is enabled in production")
        elif env == Environment.DEVELOPMENT:
            # Development-specific validations
            if not self.config.debug:
                self.warnings.append("Debug mode is disabled in development")
    
    def _is_valid_hostname(self, hostname: str) -> bool:
        """Check if hostname is valid"""
        if not hostname:
            return False
        
        # Allow localhost
        if hostname.lower() in ['localhost', '127.0.0.1', '::1']:
            return True
        
        # Check hostname format
        if len(hostname) > 253:
            return False
        
        # Check each label
        labels = hostname.split('.')
        for label in labels:
            if not label or len(label) > 63:
                return False
            if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', label):
                return False
        
        return True
    
    def _is_valid_ip_or_hostname(self, address: str) -> bool:
        """Check if address is valid IP or hostname"""
        # Try IP address first
        try:
            socket.inet_pton(socket.AF_INET, address)
            return True
        except:
            pass
        
        try:
            socket.inet_pton(socket.AF_INET6, address)
            return True
        except:
            pass
        
        # Try hostname
        return self._is_valid_hostname(address)
    
    def _is_valid_port(self, port: int) -> bool:
        """Check if port number is valid"""
        return 1 <= port <= 65535
    
    def _is_valid_url(self, url: str) -> bool:
        """Check if URL is valid"""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except:
            return False
    
    def _is_valid_ip_or_cidr(self, ip_str: str) -> bool:
        """Check if IP address or CIDR notation is valid"""
        try:
            if '/' in ip_str:
                # CIDR notation
                ip, prefix = ip_str.split('/')
                prefix_len = int(prefix)
                
                # Validate IP
                try:
                    socket.inet_pton(socket.AF_INET, ip)
                    return 0 <= prefix_len <= 32
                except:
                    pass
                
                try:
                    socket.inet_pton(socket.AF_INET6, ip)
                    return 0 <= prefix_len <= 128
                except:
                    pass
                
                return False
            else:
                # Regular IP address
                try:
                    socket.inet_pton(socket.AF_INET, ip_str)
                    return True
                except:
                    pass
                
                try:
                    socket.inet_pton(socket.AF_INET6, ip_str)
                    return True
                except:
                    pass
                
                return False
        except:
            return False


def validate_config(config: Config) -> Dict[str, Any]:
    """
    Validate configuration and return validation results
    
    Args:
        config: Configuration to validate
        
    Returns:
        Dictionary with validation results
    """
    validator = ConfigValidator(config)
    errors, warnings = validator.validate_all()
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings,
        'error_count': len(errors),
        'warning_count': len(warnings)
    }