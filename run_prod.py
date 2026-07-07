import os
import sys
from waitress import serve
from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler

# Ne asigurăm că Django știe unde se află proiectul
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Aici i-am spus să ia setările din folderul config
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings') 

# Pornim aplicația normală Django
application = get_wsgi_application()

# TRUCUL PENTRU CADDY: Împachetăm aplicația ca să servească automat și CSS/JS-ul
application = StaticFilesHandler(application)

if __name__ == '__main__':
    print("🚀 Serverul de producție Waitress a pornit pe portul 8000...")
    print("🔒 Compatibil cu reverse-proxy-ul Caddy.")
    serve(application, host='0.0.0.0', port=8000)