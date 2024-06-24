# yourapp/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('tables/<str:db_name>/', views.tables, name='tables'),
]
