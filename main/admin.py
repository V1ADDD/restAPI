from django.contrib import admin
from .models import Account, Location, AnimalType, AnimalLocation, Animal


# Register your models here.

class AccountAdmin(admin.ModelAdmin):
    list_display = ('id', 'firstName', 'lastName', 'email')
    list_display_links = ('id', 'firstName')
    search_fields = ('id', 'firstName', 'lastName', 'email')


class AnimalAdmin(admin.ModelAdmin):
    list_filter = ('gender', 'lifeStatus',)


class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'latitude', 'longitude')
    list_display_links = ('id', 'latitude', 'longitude')
    search_fields = ('id', 'latitude', 'longitude')


admin.site.register(Account, AccountAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(AnimalType)
admin.site.register(AnimalLocation)
admin.site.register(Animal, AnimalAdmin)
