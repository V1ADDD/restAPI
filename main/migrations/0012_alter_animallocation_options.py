# Generated by Django 4.1.7 on 2023-02-26 12:23

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_alter_animal_visitedlocations'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='animallocation',
            options={'ordering': ['dateTimeOfVisitLocationPoint']},
        ),
    ]
