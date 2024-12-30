# Generated by Django 4.2.4 on 2024-10-08 11:29

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bmstu_lab', '0002_rename_name_ship_title_alter_icebreaker_date_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='icebreaker',
            name='date_created',
            field=models.DateTimeField(default=datetime.datetime(2024, 10, 8, 11, 29, 20, 402977, tzinfo=datetime.timezone.utc), verbose_name='Дата создания'),
        ),
        migrations.AlterField(
            model_name='ship',
            name='image',
            field=models.CharField(blank=True, verbose_name='Изображение'),
        ),
    ]
