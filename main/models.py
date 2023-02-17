from django.db import models


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
        return self.type

    class Meta:
        ordering = ['id']
