from django.urls import path

from producer import views

urlpatterns = [
    path('', views.index, name='index'),
    path('progress/<str:key>', views.progress, name='progress'),
    path('download/<str:key>/<int:idx>', views.download_progress)
]
