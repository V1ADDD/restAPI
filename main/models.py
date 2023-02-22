from datetime import datetime

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver


# Create your models here.

class Account(models.Model):
    firstName = models.CharField(max_length=150)
    lastName = models.CharField(max_length=150)
    email = models.EmailField(max_length=150)
    password = models.CharField(max_length=150)

    def __str__(self):
        return self.firstName + " " + self.lastName

    class Meta:
        ordering = ['id']


class Location(models.Model):
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return str(self.latitude) + "x" + str(self.longitude)

    class Meta:
        ordering = ['id']


class AnimalType(models.Model):
    type = models.CharField(max_length=150)

    def __str__(self):
        return str(self.id)+". "+self.type

    class Meta:
        ordering = ['id']


class AnimalLocation(models.Model):
    dateTimeOfVisitLocationPoint = models.DateTimeField()
    locationPointId = models.ForeignKey(Location, on_delete=models.PROTECT)

    def __str__(self):
        return str(self.id)+". "+str(self.locationPointId.id)

    class Meta:
        ordering = ['dateTimeOfVisitLocationPoint']


class Animal(models.Model):
    animalTypes = models.ManyToManyField(AnimalType, blank=False)
    weight = models.FloatField()
    length = models.FloatField()
    height = models.FloatField()
    gender = models.CharField(max_length=15, choices=[('MALE', 'MALE'), ('FEMALE', 'FEMALE'), ('OTHER', 'OTHER')])
    lifeStatus = models.CharField(max_length=10, choices=[('ALIVE', 'ALIVE'), ('DEAD', 'DEAD')], default='ALIVE', blank=True)
    chippingDateTime = models.DateTimeField(auto_now_add=True, blank=True)
    chipperId = models.ForeignKey(Account, on_delete=models.PROTECT)
    chippingLocationId = models.ForeignKey(Location, on_delete=models.PROTECT)
    visitedLocations = models.ManyToManyField(AnimalLocation, blank=True)
    deathDateTime = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['id']


@receiver(pre_save, sender=Animal)
def set_death_date(sender, instance, **kwargs):
    if instance.pk:
        now = datetime.now()
        obj = sender._default_manager.get(pk=instance.id)
        if instance.lifeStatus == 'DEAD' and obj.lifeStatus != 'DEAD':
            instance.deathDateTime = now
