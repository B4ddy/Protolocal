from datetime import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  # Import settings for lazy user reference


class BaseUser(AbstractUser):
    
    class Genders(models.TextChoices):
        MANN = 'MANN', 'MANN'
        FRAU = 'FRAU', 'FRAU'
        DIVERS = 'DIVERS', 'DIVERS'

    password = None
    USERNAME_FIELD = "username"
    
    height = models.FloatField(null=True, blank=True)
    oberschenkellänge = models.FloatField(null=True, blank=True)
    unterschenkel = models.FloatField(null=True, blank=True)
    schuhgröße = models.FloatField(null=True, blank=True)
    oberkörper = models.FloatField(null=True, blank=True)
    armlänge = models.FloatField(null=True, blank=True)
    gewicht = models.FloatField(null=True, blank=True)
    geburtsdatum = models.DateField(null=True, blank=True)
    geschlecht = models.CharField(max_length=6, null=True, blank=True, choices=Genders.choices)
    sessioncount = models.IntegerField(null=True, blank=True)
    rollstuhl = models.BooleanField(null=True, blank=True)

    groups = models.ManyToManyField(
        'auth.Group', 
        related_name='baseuser_set',  
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission', 
        related_name='baseuser_permissions',  
        blank=True
    )

class ProtoSession(models.Model):
    """Unified session for both motor and sensor data"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def end_session(self):
        self.end_time = datetime.now()
        self.is_active = False
        self.save()
        
    def save(self, *args, **kwargs):
        if self.is_active:
            ProtoSession.objects.filter(user=self.user, is_active=True).update(is_active=False, end_time=datetime.now())
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Protocol Session"
        verbose_name_plural = "Protocol Sessions"


# Keep motorsession as alias for backward compatibility
motorsession = ProtoSession


class ProtoData(models.Model):
    session = models.ForeignKey(ProtoSession, on_delete=models.CASCADE, null=True, blank=True)
    actual_position = models.IntegerField()
    actual_velocity = models.IntegerField()
    phase_current = models.IntegerField()
    voltage_logic = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'timestamp']),
        ]


class SensorData(models.Model):
    session = models.ForeignKey(ProtoSession, on_delete=models.CASCADE, null=True, blank=True)
    # MPU6050 data (accelerometer and gyroscope) - Legacy sensors
    acc_x = models.FloatField(default=0.0)  # Acceleration X-axis in m/s²
    acc_y = models.FloatField(default=0.0)  # Acceleration Y-axis in m/s²
    acc_z = models.FloatField(default=0.0)  # Acceleration Z-axis in m/s²
    pitch = models.FloatField(default=0.0)  # Pitch angle in degrees
    roll = models.FloatField(default=0.0)   # Roll angle in degrees
    
    # HX711 + MPR121 data - Legacy sensors
    gewicht_N = models.FloatField(default=0.0)      # Weight/force in Newtons
    touch_status = models.IntegerField(default=0)    # Touch sensor status
    griffhoehe = models.FloatField(default=0.0)     # Grip height in cm
    
    # New Arduino A2 sensor data
    gewicht_A2 = models.FloatField(default=0.0)      # Weight/force from Arduino A2 in Newtons
    touchstatus_A2 = models.IntegerField(default=0)  # Touch sensor status from Arduino A2
    griffhoehe_A2 = models.FloatField(default=0.0)   # Grip height from Arduino A2 in cm
    
    # New Arduino A3 sensor data
    gewicht_A3 = models.FloatField(default=0.0)      # Weight/force from Arduino A3 in Newtons
    touchstatus_A3 = models.IntegerField(default=0)  # Touch sensor status from Arduino A3
    griffhoehe_A3 = models.FloatField(default=0.0)   # Grip height from Arduino A3 in cm
    
    # Sensor identifier (for when sensors exist twice per sensor)
    sensor_id = models.CharField(max_length=50, default='sensor_1')
    
    timestamp = models.DateTimeField(auto_now_add=True)  # Synchronized timestamp with ProtoData
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['sensor_id', 'timestamp']),
        ]


# Keep sensorsession as alias for backward compatibility
sensorsession = ProtoSession

    
