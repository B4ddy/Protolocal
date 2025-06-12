from django.urls import re_path
from . import motorConsumer, sensorConsumer

websocket_urlpatterns = [
    re_path(r'ws/motor_control/$', motorConsumer.MotorConsumer.as_asgi()),
    re_path(r'ws/sensor_control/$', sensorConsumer.SensorConsumer.as_asgi())
]

