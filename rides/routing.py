from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/ride/<int:ride_id>/', consumers.RideConsumer.as_asgi()),
]