from django.urls import path
from . import views

app_name = 'rides'

urlpatterns = [
    path('landing/', views.landing, name='landing'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('request_ride/', views.request_ride, name='request_ride'),
    path('ride_status/<int:ride_id>/', views.get_ride_status, name='ride_status'),

    path('driver/', views.driver_dashboard, name='driver_dashboard'),

    path('accept_ride/<int:ride_id>/', views.accept_ride, name='accept_ride'),
    path('reach_pickup/<int:ride_id>/', views.reach_pickup, name='reach_pickup'),
    path('verify_pickup_otp/<int:ride_id>/', views.verify_pickup_otp, name='verify_pickup_otp'),
    path('start_ride/<int:ride_id>/', views.start_ride, name='start_ride'),
    path('reach_destination/<int:ride_id>/', views.reach_destination, name='reach_destination'),
    path('complete_ride/<int:ride_id>/', views.complete_ride, name='complete_ride'),
    path('customer_ack/<int:ride_id>/', views.customer_acknowledge_ride, name='customer_acknowledge_ride'),
    path('pay_cash/<int:ride_id>/', views.pay_cash, name='pay_cash'),
    path('feedback/<int:ride_id>/', views.submit_ride_feedback, name='submit_ride_feedback'),

    path('update_location/', views.update_location, name='update_location'),

    path('send_message/', views.send_message, name='send_message'),
    path('get_messages/<int:ride_id>/', views.get_messages, name='get_messages'),

    path('driver-tickets/', views.driver_tickets, name='driver_tickets'),
    path('acknowledge-ticket/<str:ticket_id>/', views.acknowledge_ticket, name='acknowledge_ticket'),

    path('upload-recording/<int:ride_id>/', views.upload_recording, name='upload_recording'),
    path('admin-recordings/', views.admin_recordings),
]

# MEDIA (IMPORTANT)
from django.conf import settings
from django.conf.urls.static import static
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)