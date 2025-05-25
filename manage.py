"""
Endpoint for all of Django's administrative tasks.
"""

import os
import sys
from dotenv import load_dotenv
# from utils.general import fetch_default_module


load_dotenv()
# settings_module= fetch_default_module()

def main():
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.deploy')
    try:
        from django.core.management import execute_from_command_line
        execute_from_command_line(sys.argv)

    except ImportError as impt_err:
        raise ImportError(
            "Couldn't import Django. Make sure it is installed and available\n"
            "on your PYTHONPATH environment variable. Or did you forget to\n"
            "activate virtual environment?\n"
        ) from impt_err

    except Exception as exc:
        print(f"UNEXPECTED ERROR- An unexpected error occurred: {str(exc)}")


if __name__=='__main__':
    main()