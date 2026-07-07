from django.apps import AppConfig
import os

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'  # <--- Aici era problema

    def ready(self):
        # RUN_MAIN previne pornirea dublă a robotului
        if os.environ.get('RUN_MAIN'):
            from . import scheduler
            scheduler.start_scheduler()