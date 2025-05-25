"""
Serves all base requirements for Django application configuration.
"""

import os
from pathlib import Path
from typing import List
from functools import lru_cache
from dotenv import load_dotenv


load_dotenv()

class BaseConfiguration:
    """Base configuration for Django. Extensible by environment-specific classes."""

    required_vars:list=[] # Subclasses override this

    def __init__(self)->None:
        self._secret_key:str=os.environ.get('DJANGO_SECRET_KEY')
        self.base_dir:Path=Path(__file__).resolve().parent.parent.parent
        self._env:str=os.environ.get('DJANGO_ENV')
        self._csrf_trusted_origins:List[str]=[]
        self._validate_environment()

        self.lang_code:str='en-us'
        self.time_zone:str='UTC'
        self.use_international:bool=True
        self.use_localization:bool=True
        self.use_tz:bool=True

    def _validate_environment(self):
        """Validates environment variables."""
        missing_vars:list[str]=[var for var in self.required_vars if not os.environ.get(var, '').strip()]
        if missing_vars:
            raise EnvironmentError(f"ERROR- Missing required environment variables: {', '.join(missing_vars)}")

    @property
    def fetch_django_env(self)->str:
        """Determines Django preferred environment."""
        return self._env

    @property
    def fetch_secret_key(self)->str:
        """Secure secret key fetcher."""
        return self._secret_key

    @property
    def allowed_hosts(self)->List[str]:
        """Parse allowed hosts from environment variable."""
        hosts=os.environ.get('DJANGO_ALLOWED_HOSTS')
        return hosts.split(', ') if hosts else ['localhost', '127.0.0.1']

    @property
    def installed_apps(self)->List[str]:
        """List deployed Django apps."""
        third_party:List[str]=[]
        project_apps:List[str]=[]
        return third_party+project_apps

    @property
    def middleware(self)->List[str]:
        """List middleware classes."""
        return [
            'django.middleware.security.SecurityMiddleware',
            'django.middleware.common.CommonMiddleware',
            'corsheaders.middleware.CorsMiddleware',
            'apps.core.middleware.RequestLoggerMiddleware',
        ]

    @property
    def root_urlconf(self)->str:
        """Returns URL path configurations."""
        return 'config.urls'

    @property
    def csrf_trusted_origins(self)->List:
        """Lists security trusted origins."""
        return self._csrf_trusted_origins


@lru_cache(maxsize=1)
def get_config()->BaseConfiguration:
    """Fetch cached configuration instance."""
    return BaseConfiguration()


# To be exported to deploy.serveDjangoConfig.py

config:BaseConfiguration=get_config()

BASE_DIR:Path= config.base_dir
env:str= config.fetch_django_env
if env.lower()=='development':
    DEBUG:bool=True # Temporary config for testing purposes
SECRET_KEY:str=config.fetch_secret_key
ALLOWED_HOSTS:List[str]=config.allowed_hosts
ROOT_URLCONF:str=config.root_urlconf
CSRF_TRUSTED_ORIGINS:List[str]=config.csrf_trusted_origins