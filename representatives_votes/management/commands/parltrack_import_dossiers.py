# coding: utf-8
import os
import urllib
import ijson

from django.core.management.base import BaseCommand

from representatives.management.parltrack import retrieve_xz_json
from representatives_votes.models import Dossier
from import_parltrack_dossier import parse_dossier_data


URL = 'http://parltrack.euwiki.org/dumps/ep_dossiers.json.xz'
LOCAL_PATH = 'ep_dossiers.json.xz'


class Command(BaseCommand):
    """
    Import Dossiers from parltrack.
    """

    def handle(self, *args, **options):
        path = retrieve_xz_json(URL, LOCAL_PATH)

        with open(path, 'r') as f:
            for dossier in ijson.items(f, 'item'):
                parse_dossier_data(dossier)
