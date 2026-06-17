from django.apps import AppConfig


class ClassConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'class'
    verbose_name = "Classes & Lessons"
    
    def ready(self):
        """Import signals when app is ready"""
        from . import signals
