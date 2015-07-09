# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('representatives', '0003_auto_20150702_1827'),
        ('import_parltrack_votes', '0001_squashed_0002_auto_20150520_1008'),
    ]

    operations = [
        migrations.AddField(
            model_name='matching',
            name='representative',
            field=models.ForeignKey(to='representatives.Representative', null=True),
        ),
    ]
