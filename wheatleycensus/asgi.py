
# wheatleycensus/asgi.py
# Entry point for ASGI servers to run the Django app in production.
# Sets up the ASGI application callable for deployment.

import os
from django.core.asgi import get_asgi_application

# Set the default settings module for the 'wheatleycensus' project
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wheatleycensus.settings')

# ASGI application callable
application = get_asgi_application()
