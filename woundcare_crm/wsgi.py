"""WSGI config for woundcare_crm project."""
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "woundcare_crm.settings")
application = get_wsgi_application()
