"""
WSGI config for wheatleycensus project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import sys
import os

project_home = '/home/senchyne/Wheatley_Census'  # folder with manage.py
if project_home not in sys.path:
    sys.path.append(project_home)

# # Activate virtualenv
# activate_this = '/home/senchyne/venv-wheatley-new/bin/activate_this.py'
# with open(activate_this) as f:
#     exec(f.read(), {'__file__': activate_this})

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'wheatleycensus.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

