# coding: utf-8
from django.core.management.base import BaseCommand
from representatives_votes.models import Dossier

PARLTRACK_URL = 'http://parltrack.euwiki.org/dossier/%s?format=json'

class Command(BaseCommand):

    def handle(self, *args, **options):
        Dossier.objects.all().delete()
