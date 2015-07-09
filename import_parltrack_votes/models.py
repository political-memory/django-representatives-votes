# coding: utf-8

# Matching table for ugly data from parltrack to representative

from django.db import models

from representatives.models import Representative

class Matching(models.Model):
    representative = models.ForeignKey(Representative, null=True)
    mep_name = models.CharField(max_length=200)
    mep_group = models.CharField(max_length=200)
