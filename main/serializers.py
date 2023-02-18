from rest_framework import serializers
from .models import Account, Location, AnimalType, AnimalLocation, Animal


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'


class AnimalTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalType
        fields = '__all__'


class AnimalLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnimalLocation
        fields = '__all__'


class AnimalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Animal
        fields = ('id', 'animalTypes', 'weight', 'length', 'height', 'gender',
                  'lifeStatus', 'chippingDateTime', 'chipperId', 'chippingLocationId',
                  'visitedLocations', 'deathDateTime')
