from django.apps import AppConfig


class LocalDatabaseConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'local_database'
