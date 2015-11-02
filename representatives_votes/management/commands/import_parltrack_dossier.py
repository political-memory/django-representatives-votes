# coding: utf-8

import urllib
import json

from os.path import join
from slugify import slugify

from django.core.management.base import BaseCommand
from import_parltrack_votes.utils import parse_dossier_data

PARLTRACK_URL = 'http://parltrack.euwiki.org/dossier/{}?format=json'

class Command(BaseCommand):
    """
    Import a Dossier from parltrack and save it in the
    representatives_votes model format
    """

    def add_arguments(self, parser):
        # parser.add_argument('--celery', action='store_true', default=False)
        parser.add_argument('dossier_id')

    def handle(self, *args, **options):
        dossier_id = unicode(options['dossier_id'])
        parltrack_url = PARLTRACK_URL.format(dossier_id)

        json_dump_localization = join("/tmp", "dossier_{}.json".format(slugify(dossier_id)))
        # print json_dump_localization
        
        urllib.urlretrieve(parltrack_url, json_dump_localization)
        dossier_data = json.load(open(json_dump_localization))
        parse_dossier_data(dossier_data)
