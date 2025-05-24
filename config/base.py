"""
Serves all base requirements for Django application configuration.
"""
import os
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

BASE_DIR:Path=Path(__file__).resolve().parent.parent.parent
DEBUG:bool=True
SECRET_KEY:str=os.environ.get('DJANGO_SECRET_KEY')
ALLOWED_HOSTS=['localhost', '127.0.0.1']
DATABASES:Dict[str, Dict[str, Any]]={
    'default':{
        'ENGINE':'django.db.backends.sqlite3',
        'NAME':str(BASE_DIR/'db.sqlite3')
    }
}
ROOT_URLCONF:str='config.urls'