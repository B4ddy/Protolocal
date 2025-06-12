from datetime import datetime
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings  # Import settings for lazy user reference


class baseuser(AbstractUser):
    
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

class protosession(models.Model):
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
            protosession.objects.filter(user=self.user, is_active=True).update(is_active=False, end_time=datetime.now())
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Protocol Session"
        verbose_name_plural = "Protocol Sessions"


# Keep motorsession as alias for backward compatibility
motorsession = protosession


class protodata(models.Model):
    session = models.ForeignKey(protosession, on_delete=models.CASCADE, null=True, blank=True)
    actual_position = models.IntegerField()
    actual_velocity = models.IntegerField()
    phase_current = models.IntegerField()
    voltage_logic = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'timestamp']),
        ]


class sensordata(models.Model):
    session = models.ForeignKey(protosession, on_delete=models.CASCADE, null=True, blank=True)
    # MPU6050 data (accelerometer and gyroscope)
    acc_x = models.FloatField()  # Acceleration X-axis in m/s²
    acc_y = models.FloatField()  # Acceleration Y-axis in m/s²
    acc_z = models.FloatField()  # Acceleration Z-axis in m/s²
    pitch = models.FloatField()  # Pitch angle in degrees
    roll = models.FloatField()   # Roll angle in degrees
    
    # HX711 + MPR121 data
    gewicht_N = models.FloatField()      # Weight/force in Newtons
    touch_status = models.IntegerField()  # Touch sensor status
    griffhoehe = models.FloatField()     # Grip height in cm
    
    # Sensor identifier (for when sensors exist twice per sensor)
    sensor_id = models.CharField(max_length=50, default='sensor_1')
    
    timestamp = models.DateTimeField(auto_now_add=True)  # Synchronized timestamp with protodata
    
    class Meta:
        indexes = [
            models.Index(fields=['session', 'timestamp']),
            models.Index(fields=['sensor_id', 'timestamp']),
        ]


# Keep sensorsession as alias for backward compatibility
sensorsession = protosession

    
