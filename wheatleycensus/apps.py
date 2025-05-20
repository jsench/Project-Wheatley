# wheatleycensus/apps.py
# Django AppConfig for the Wheatley Census application.
# This class is used by Django to configure app-specific settings and behaviors.

from django.apps import AppConfig

class WheatleycensusConfig(AppConfig):
    """
    Configuration for the Wheatley Census Django app.
    Used by Django to identify and configure the app.
    """
    name = 'wheatleycensus'
