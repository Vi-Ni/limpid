from django.contrib import admin

from .models import Asset


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ["ticker", "name", "asset_type", "currency", "current_price"]
    list_filter = ["asset_type", "currency", "geography"]
    search_fields = ["ticker", "name"]
