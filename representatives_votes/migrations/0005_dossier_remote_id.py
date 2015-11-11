# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('representatives_votes', '0004_auto_20150709_0819'),
    ]

    operations = [
        migrations.AddField(
            model_name='dossier',
            name='remote_id',
            field=models.CharField(default='', unique=True, max_length=255),
            preserve_default=False,
        ),
    ]
