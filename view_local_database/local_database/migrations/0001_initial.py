# Generated by Django 4.2.9 on 2024-02-05 09:25

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Table',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('db_name', models.CharField(max_length=100)),
                ('table_name', models.CharField(max_length=100)),
            ],
        ),
    ]