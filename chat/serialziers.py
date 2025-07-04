from django.contrib.auth.models import User
from rest_framework import serializers
from .models import *


class ProtoDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProtoData
        fields = ["actual_position", "actual_velocity",
                  "phase_current", "voltage_logic", "timestamp"]


class ProtoDataFullSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProtoData
        fields = '__all__'  # Serialize all fields in the ProtoData model


class BaseUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = BaseUser
        fields = '__all__'  # Serialize all fields in the BaseUser model




class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=150)  # Or whatever your username field allows
    height = serializers.FloatField( allow_null=True, required=False)     # This allows null for height
    oberschenkellänge = serializers.FloatField( allow_null=True, required=False )  #allows null, doesn't require field
    unterschenkel = serializers.FloatField( allow_null=True, required=False)
    schuhgröße = serializers.FloatField( allow_null=True, required=False)
    oberkörper = serializers.FloatField( allow_null=True, required=False)
    armlänge = serializers.FloatField( allow_null=True, required=False)
    gewicht = serializers.FloatField( allow_null=True, required=False)
    geburtsdatum = serializers.DateField( allow_null=True, required=False)
    geschlecht = serializers.CharField( allow_null=True, required=False)  # Adjust max_length as needed
    sessioncount = serializers.IntegerField( allow_null=True, required=False)  # No allow_null specified, so defaults to False
    rollstuhl = serializers.BooleanField( allow_null=True, required=False)
    id = serializers.IntegerField(read_only=True) # Important:  Should be read-only

    class Meta:
        model = BaseUser
        fields = ["username","height","oberschenkellänge","unterschenkel","schuhgröße","oberkörper",
                  "armlänge","gewicht","geburtsdatum","geschlecht","sessioncount","rollstuhl","id"]

    def create(self, validated_data):
        user = BaseUser.objects.create_user(**validated_data)
        return user
   
class SessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProtoSession
        fields = '__all__'  # Serialize all fields in the Session model