# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('import_parltrack_votes', '0002_matching_representative'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='matching',
            name='representative_remote_id',
        ),
    ]
