# Generated by Django 4.2.4 on 2024-12-21 08:24

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bmstu_lab', '0028_alter_icebreaker_date_created'),
    ]

    operations = [
        migrations.AlterField(
            model_name='icebreaker',
            name='result',
            field=models.BooleanField(null=True, verbose_name='Результат проводки (0/1)'),
        ),
    ]
