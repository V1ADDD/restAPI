# Generated by Django 4.1.7 on 2023-02-18 19:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_alter_animal_gender_alter_animal_lifestatus'),
    ]

    operations = [
        migrations.AlterField(
            model_name='animal',
            name='visitedLocations',
            field=models.ManyToManyField(blank=True, to='main.animallocation'),
        ),
    ]
