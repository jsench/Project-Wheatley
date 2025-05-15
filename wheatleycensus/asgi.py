"""
ASGI config for marlowecensus project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

# wheatleycensus/asgi.py
# Entry point for ASGI servers to run the Django app in production.

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wheatleycensus.settings')

application = get_asgi_application()
