from django.urls import path
from .views import HomeView, motor, sensor, userkeys, token_default, create_proto_data, createuser,UpdateUserView, Get_User,GetUserView,GetActiveSessionView,DeleteUserView, StartSessionView, StopSessionView, MotorDataView,GetSessionView, GetSessionDataView, current_datetime, StartSensorSessionView, StopSensorSessionView, GetActiveSensorSessionView, GetSensorSessionView, GetSensorSessionDataView

urlpatterns = [
    path("motor", motor),
    path("sensor", sensor),
    path("current_datetime", current_datetime, name="current_datetime"),
    path("token_default", token_default), 
    path('createdata', create_proto_data, name='create_proto_data'),
   
    #userverwatung
   
    path("createuser",createuser ),  #create user
    path("get_users",Get_User.as_view()),     #list of all users
    path("userkeys",userkeys ),      #get acess and refresh token for username
    path("get_current_user", GetUserView.as_view()),
    
    
    #sessionverwaltung
    
    path("start_session",StartSessionView.as_view()),
    path('stop_session/<int:session_id>/', StopSessionView.as_view(), name='stop_session'),
    path("get_session",GetSessionView.as_view()),
    path("get_active_session",GetActiveSessionView.as_view()),

    path("motordataview", MotorDataView.as_view()),
    path('get_session_data/<int:session_id>/', GetSessionDataView.as_view(), name='get_session_data'),
    
    # Sensor session management
    path("start_sensor_session", StartSensorSessionView.as_view()),
    path('stop_sensor_session/<int:session_id>/', StopSensorSessionView.as_view(), name='stop_sensor_session'),
    path("get_sensor_session", GetSensorSessionView.as_view()),
    path("get_active_sensor_session", GetActiveSensorSessionView.as_view()),
    path('get_sensor_session_data/<int:session_id>/', GetSensorSessionDataView.as_view(), name='get_sensor_session_data'),
    path('update_user', UpdateUserView.as_view(), name='update_user'),
    path('delete_user', DeleteUserView.as_view(), name='delete_user'),
    
]

#token= standard jwt token
#token2= defaultusertoken
#tokentest
#tokentest=needs authenticated