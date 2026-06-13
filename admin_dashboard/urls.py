from django.urls import path
from . import views

app_name = 'admin_dashboard'
urlpatterns = [
    path('', views.dashboard, name='admin_dashboard'),
    path('stats.json', views.stats_api, name='stats_api'),
    path('create-user/', views.create_user, name='create_user'),
    path('ride-history/', views.ride_history, name='ride_history'),
    path('resolve/<str:ticket_id>/', views.resolve_ticket, name='resolve_ticket'),
    path('assign-driver/<int:ride_id>/', views.assign_driver, name='assign_driver'),
    path('update-status/<int:ride_id>/', views.update_ride_status, name='update_ride_status'),
]