from django.urls import path

from producer import views

urlpatterns = [
    path('', views.index, name='index')
]
