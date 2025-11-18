from django.apps import AppConfig


class CrmappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crmapp'

    def ready(self):
        # Start scheduler only when server starts (not during migrations)
        from django.conf import settings
        if settings.DEBUG:
            from .scheduler import start_scheduler
            start_scheduler()
