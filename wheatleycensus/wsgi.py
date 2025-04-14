import sys
import os

# path to your project folder
project_home = '/home/senchyne/wheatleycensus'
if project_home not in sys.path:
    sys.path.append(project_home)

# If your Django settings file is in wheatleycensus/settings.py
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wheatleycensus.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

