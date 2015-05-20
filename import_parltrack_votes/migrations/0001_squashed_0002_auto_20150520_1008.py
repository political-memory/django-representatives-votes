# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    replaces = [(b'import_parltrack_votes', '0001_initial'), (b'import_parltrack_votes', '0002_auto_20150520_1008')]

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Matching',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('representative_remote_id', models.CharField(max_length=200, null=True)),
                ('mep_name', models.CharField(max_length=200)),
                ('mep_group', models.CharField(max_length=200)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
