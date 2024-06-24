from django.db import models
class Table(models.Model):
    db_name = models.CharField(max_length=100)
    table_name = models.CharField(max_length=100)
# Create your models here.
