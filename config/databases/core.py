import os
from functools import lru_cache
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


# Custom exceptions (to be exported from utilities later)
class DatabaseConfigurationError(Exception):
    """Base exception for database configuration errors."""
    pass

class MissingEnvironmentVariableError(DatabaseConfigurationError):
    """Raised when required environment variables are missing."""
    pass

class UnsupportedDatabaseError(DatabaseConfigurationError):
    """Raised when attempting to use an unsupported database configuration."""
    pass

class DatabaseConnectionError(DatabaseConfigurationError):
    """Raised when database connection fails."""
    pass


# Configuration Data Classes
@dataclass
class DatabaseCredentials:
    """Encapsulates database connection credentials."""
    name:str
    user:Optional[str]=None
    password:Optional[str]=None
    host:Optional[str]=None
    port:Optional[int]=None

    def __post_init__(self):
        """Validate credentials based on database requirements."""
        if not self.name:
            raise ValueError("Database name is required.")


@dataclass
class DatabaseOptions:
    """Database-specific options and configurations."""
    charset:Optional[str]=None
    timezone:Optional[str]=None
    atomic_requests:bool=False
    autocommit:bool=True
    conn_max_age:int=0
    options:Optional[Dict[str, Any]]=None

    def __post_init__(self):
        if self.options is None:
            self.options={}


# Abstract Base Configuration
class BaseDatabaseConfiguration(ABC):
    """
    Abstract base class for all database configurations.
    Defines the contract all database configurations must follow.
    """
    # Class-level configuration
    ENGINE_NAME:str=''
    DEFAULT_PORT:Optional[int]=None
    REQUIRED_ENV_VARS:List[str]=[]
    OPTIONAL_ENV_VARS:List[str]=[]

    def __init__(self, environment_prefix:str="DB"):
        """
        Initialize database configuration.
        Args:
            environment_prefix: Prefix for environment variables (default:"DB")
        """

        self.env_prefix=environment_prefix
        self.logger=logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        # Load configuration
        self.credentials=self._load_credentials()
        self.options=self._load_options()

        # Validate configuration
        self._validate_configuration()

    def _get_env_var(self, var_name:str, default:Any=None, required:bool=False)->Any:
        """
        Get environment variable with proper error handling.
        Args:
            var_name: Name of the environment variable (without prefix)
            default: Default value if variable is not set
            required: Whether the variable is required by configuration or not

        Returns:
            Environment variable value or default value (if none is provided)

        Raises:
            MissingEnvironmentVariableError: If required variable is missing
        """
        full_var_name=f"{self.env_prefix}_{var_name}"
        value=os.environ.get(full_var_name, default)

        if required and (value is None or str(value).strip()==''):
            raise MissingEnvironmentVariableError(
                f"Required environment variable '{full_var_name}' is missing or is empty"
            )

        return value

    def _load_credentials(self):
        """Load database credentials from environment variables."""
        return DatabaseCredentials(
            name=self._get_env_var('NAME', required=True),
            user=self._get_env_var('USER'),
            password=self._get_env_var('PASSWORD'),
            host=self._get_env_var('HOST'),
            port=self._get_env_var('PORT')
        )

    def _load_options(self)->DatabaseOptions:
        """Load database options from environment variables."""
        return DatabaseOptions(
            charset=self._get_env_var('CHARSET'),
            timezone=self._get_env_var('TIMEZONE'),
            atomic_requests=self._parse_boolean(self._get_env_var('ATOMIC_REQUEST', 'false')),
            conn_max_age=int(self._get_env_var('CONN_MAX_AGE', 0)),
            options=self._load_custom_options()
        )

    def _parse_port(self, port_value:Any)->Optional[int]:
        """Parse port number from string."""
        if port_value is None:
            return self.DEFAULT_PORT
        try:
            return int(port_value)
        except (ValueError, TypeError):
            self.logger.warning(f"Invalid port value: {port_value}, using default: {self.DEFAULT_PORT}")
            return self.DEFAULT_PORT

    @staticmethod
    def _parse_boolean(value:str)->bool:
        """Parse boolean from string."""
        return str(value).lower() in ('true', '1', 'yes', 'on')

    def _load_custom_options(self)->Dict[str, Any]:
        """Load custom database-specific options."""
        options={}

        # Load options from environment variables with OPTIONS_ prefix
        for key, value in os.environ.items():
            if key.startswith(f"{self.env_prefix}_OPTIONS_"):
                option_key=key[len(f"{self.env_prefix}_OPTIONS_"):].lower()
                options[option_key]=value

        return options

    def _validate_configuration(self)->None:
        """Validates loaded configurations."""
        # Validates required environment variables
        missing_vars=[]
        for var in self.REQUIRED_ENV_VARS:
            if not self._get_env_var(var):
                missing_vars.append(f"{self.env_prefix}_{var}")

        if missing_vars:
            raise MissingEnvironmentVariableError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )

        # Perform database-specific validation
        self._validate_database_specific()

    @abstractmethod
    def _validate_database_specific(self)->None:
        """Perform database-specific validation."""
        pass

    @abstractmethod
    def get_django_config(self)->Dict[str, Any]:
        """Generate Django database configuration database."""
        pass

    @staticmethod
    def test_connection()->bool:
        """Test database connection (to be implemented by subclasses)."""
        return True

    def get_connection_string(self)->str:
        """Generate connection string for database connection."""
        return f"{self.ENGINE_NAME}://{self.credentials.user}@{self.credentials.host}:{self.credentials.port}/{self.credentials.name}"


# Concrete database implementations (to be exported from respective directory appropriately)
class PostgreSQLConfiguration(BaseDatabaseConfiguration):
    """PostgreSQL database configuration."""
    ENGINE_NAME='django.db.backends.postgresql'
    DEFAULT_PORT=5432
    REQUIRED_ENV_VARS=['NAME', 'USER', 'PASSWORD', 'HOST']
    OPTIONAL_ENV_VARS=['PORT', 'CHARSET', 'TIMEZONE']

    def _validate_database_specific(self)->None:
        """Validate PostgreSQL-specific requirements."""
        if not self.credentials.user:
            raise DatabaseConfigurationError('PostgreSQL requires a username')
        if not self.credentials.password:
            raise DatabaseConfigurationError('PostgreSQL requires a password')
        if not self.credentials.host:
            raise DatabaseConfigurationError('PostgreSQL requires a host')

    def get_django_config(self)->Dict[str, Any]:
        """Generates Django configuration for PostgreSQL."""
        config={
            'ENGINE': self.ENGINE_NAME,
            'NAME':self.credentials.name,
            'USER':self.credentials.user,
            'PASSWORD':self.credentials.password,
            'HOST':self.credentials.host,
            'PORT':self.credentials.port or self.DEFAULT_PORT,
            'ATOMIC_REQUESTS':self.options.atomic_requests,
            'AUTOCOMMIT':self.options.autocommit,
            'CONN_MAX_AGE':self.options.conn_max_age,
            'OPTIONS':self.options.options.copy()
        }

        # Add PostgreSQL-specific options
        if self.options.charset:
            config['OPTIONS']['charset']=self.options.charset
            if self.options.timezone:
                config['TIME_ZONE']=self.options.timezone

        return config

class MySQLConfiguration(BaseDatabaseConfiguration):
    """MySQL database configurations."""
    ENGINE_NAME='django.db.backends.mysql'
    DEFAULT_PORT=3306
    REQUIRED_ENV_VARS=['NAME', 'USER', 'PASSWORD', 'HOST']
    OPTIONAL_ENV_VARS=['PORT', 'CHARSET', 'TIMEZONE']

    def _validate_database_specific(self)->None:
        """Validates MySQL-specific requirements."""
        if not self.credentials.user:
            raise DatabaseConfigurationError('MySQL requires a username')
        if not self.credentials.password:
            raise DatabaseConfigurationError('MySQL requires a password')
        if not self.credentials.host:
            raise DatabaseConfigurationError('MySQL requires a host')

    def get_django_config(self)->Dict[str, Any]:
        """Generates Django configurations for MySQL."""
        config={
            'ENGINE':self.ENGINE_NAME,
            'NAME':self.credentials.name,
            'USER':self.credentials.user,
            'PASSWORD':self.credentials.password,
            'HOST':self.credentials.host,
            'PORT':self.credentials.port or self.DEFAULT_PORT,
            'ATOMIC_REQUESTS':self.options.atomic_requests,
            'AUTOCOMMIT':self.options.autocommit,
            'CONN_MAX_AGE':self.options.conn_max_age,
            'OPTIONS':self.options.options.copy()
        }

        # Add MySQL-specific options
        if self.options.charset:
            config['OPTIONS']['charset']=self.options.charset
        if self.options.timezone:
            config['OPTIONS'][
                'init_command']=f"SET sql_mode='STRICT_TRANS_TABLES'; SET time_zone='{self.options.timezone}'"

        return config


class SQLiteConfiguration(BaseDatabaseConfiguration):
    """SQLite database configuration."""
    ENGINE_NAME='django.db.backends.sqlite3'
    DEFAULT_PORT=None
    REQUIRED_ENV_VARS=['NAME']
    OPTIONAL_ENV_VARS=[]

    def __init__(self, environment_prefix:str='DB', base_dir:Optional[str]=None):
        """
        Initialize SQLite configuration.
        Args:
            environment_prefix: Prefix for environment variables
            base_dir: Base directory for relative database paths
        """
        self.base_dir=base_dir
        super().__init__(environment_prefix=environment_prefix)

    def _load_credentials(self)->DatabaseCredentials:
        """Load SQLite credentials (just the database path)."""
        db_name=self._get_env_var('NAME', 'db.sqlite3', required=True)

        # Handle relative paths
        if self.base_dir and not os.path.isabs(db_name):
            db_name=os.path.join(self.base_dir, db_name)

        return DatabaseCredentials(name=db_name)

    def _validate_database_specific(self)->None:
        """Validates SQLite-specific requirements."""
        # Ensure directory exists for the database file
        db_dir=os.path.dirname(self.credentials.name)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
            except OSError as os_err:
                raise DatabaseConfigurationError(f"Cannot create directory for SQLite database: {os_err}")

    def get_django_config(self)->Dict[str, Any]:
        """Generates Django configuration for SQLite."""
        return {
            'ENGINE':self.ENGINE_NAME,
            'NAME':self.credentials.name,
            'ATOMIC_REQUESTS':self.options.atomic_requests,
            'AUTOCOMMIT':self.options.autocommit,
            'CONN_MAX_AGE':self.options.conn_max_age,
            'OPTIONS':self.options.options.copy()
        }


# Database Factory and Registry
class DatabaseConfigurationFactory:
    """Factory for creating database configurations."""

    _registry:Dict[str, Type[BaseDatabaseConfiguration]]={
        'postgresql':PostgreSQLConfiguration,
        'postgres':PostgreSQLConfiguration,
        'mysql':MySQLConfiguration,
        'sqlite':SQLiteConfiguration,
        'sqlite3':SQLiteConfiguration,
    }

    @classmethod
    def register_database(cls, name:str, config_class:Type[BaseDatabaseConfiguration])->None:
        """
        Register a new database configuration class.
        Args:
            name: Database name identifier
            config_class: Configuration class
        """
        if not issubclass(config_class, BaseDatabaseConfiguration):
            raise TypeError('Configuration class must inherit from BaseDatabaseConfiguration')
        cls._registry[name.lower()]=config_class

    @classmethod
    def create(cls, database_type:str, **kwargs)->BaseDatabaseConfiguration:
        """
        Creates a database configuration instance.
        Args:
            database_type: Type of database (postgresql, mysql, sqlite, etc.)
            **kwargs: Additional arguments to pass to the configuration class

        Returns:
            Database configuration instance

        Raises:
            UnsupportedDatabaseError: If database type is not supported
        """
        database_type=database_type.lower()
        if database_type not in cls._registry:
            available_types=', '.join(cls._registry.keys())
            raise UnsupportedDatabaseError(
                f"Unsupported database type: {database_type}."
                f"Available types: {available_types}."
            )

        config_class=cls._registry[database_type]
        return config_class(**kwargs)

    @classmethod
    def get_available_databases(cls)->List[str]:
        """Get list of available database types."""
        return list(cls._registry.keys())


# Main Configuration Manager
class DatabaseManager:
    """Main database configuration manager."""
    def __init__(self, base_dir:Optional[str]=None):
        """
        Initialize database manager.
        Args:
            base_dir: Base directory for relative paths (typically Django's BASE_DIR)
        """
        self.base_dir=base_dir
        self.logger=logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @lru_cache(maxsize=1)
    def get_configuration(self, environment_prefix:str='DB')->BaseDatabaseConfiguration:
        """
        Fetch database configuration based on environment variables.
        Args:
            environment_prefix: Prefix for environment variables

        Returns:
            Cached database configuration instance

        Raises:
            DatabaseConfigurationError: If configuration fails
        """
        database_type=os.environ.get(f"{environment_prefix}_ENGINE")

        if not database_type:
            self.logger.info("No database engine specified, defaulting to SQLite.")
            return SQLiteConfiguration(environment_prefix,self.base_dir)

        # Map Django engine names to types
        engine_mapping={
            'django.db.backends.postgresql':'postgresql',
            'django.db.backends.mysql':'mysql',
            'django.db.backends.sqlite3':'sqlite',
        }

        # Check if it's a full Django engine name
        if database_type in engine_mapping:
            database_type=engine_mapping[database_type]

        try:
            if database_type.lower()=='sqlite':
                return DatabaseConfigurationFactory.create(database_type,
                                                           environment_prefix=environment_prefix,
                                                           base_dir=self.base_dir)
            else:
                return DatabaseConfigurationFactory.create(database_type,
                                                           environment_prefix=environment_prefix)
        except Exception as exc:
            self.logger.error(f"Failed to create database configuration: {exc}")
            raise DatabaseConfigurationError(f"Database configuration failed: {exc}")

    def get_django_databases_config(self, databases:Dict[str, str]=None)->Dict[str, Any]:
        """
        Get Django DATABASES configuration for multiple databases.

        Args:
            databases: Dictionary mapping database alias to environment prefix

        Returns:
            Django DATABASES configuration dictionary
        """

        if databases is None:
            databases= {'default': 'DB'}

        config={}
        for alias, env_prefix in databases.items():
            try:
                db_config=self.get_configuration(env_prefix)
                config[alias]=db_config.get_django_config()
                self.logger.info(f"Configuration database '{alias}' with {db_config.__class__.__name__}")

            except Exception as exc:
                self.logger.error(f"Failed to configure database '{alias}': {exc}")
                # Fallback to SQLite for failed configurations
                fallback_config=SQLiteConfiguration(env_prefix, self.base_dir)
                config[alias]=fallback_config.get_django_config()
                self.logger.warning(f"Defaulting to SQLite fallback for database '{alias}'")

        return config