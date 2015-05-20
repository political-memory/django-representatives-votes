# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('import_parltrack_votes', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='matching',
            name='representative_remote_id',
            field=models.CharField(max_length=200, null=True),
            preserve_default=True,
        ),
    ]
