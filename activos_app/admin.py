from django.contrib import admin

from .models import Hardware


@admin.register(Hardware)
class HardwareAdmin(admin.ModelAdmin):
    list_display = ("hardware_id", "hardware", "sistema_operativo")
    search_fields = ("hardware", "sistema_operativo")
