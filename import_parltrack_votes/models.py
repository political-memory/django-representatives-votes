# coding: utf-8

# Matching table for ugly data from parltrack to representative

from django.db import models

class Matching(models.Model):
    representative_remote_id = models.CharField(max_length=200, null=True)
    mep_name = models.CharField(max_length=200)
    mep_group = models.CharField(max_length=200)
