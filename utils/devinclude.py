import sys,os
from os.path import dirname, realpath

sys.path.insert(0, dirname(dirname(realpath(__file__))))
os.environ['DJANGO_SETTINGS_MODULE'] = 'bctip.settings'
import loadenv

from django.conf import settings
sys.path.append(settings.PROJECT_DIR)

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
