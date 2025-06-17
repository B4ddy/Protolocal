from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import BaseUser, motorsession

# Register User model
class CustomUserAdmin(UserAdmin):
    model = BaseUser
admin.site.register(BaseUser, CustomUserAdmin)

# Register motorsession model with appropriate admin class
class MotorSessionAdmin(admin.ModelAdmin):
    model=motorsession

admin.site.register(motorsession, MotorSessionAdmin)