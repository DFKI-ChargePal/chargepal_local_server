from django.shortcuts import render
from django.db import connections

def index(request):
    databases = connections.all()
    return render(request, 'local_database/index.html', {'databases': databases})

def tables(request, db_name):
    with connections[db_name].cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
    return render(request, 'local_database/tables.html', {'db_name': db_name, 'tables': tables})
