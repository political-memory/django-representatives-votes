# coding: utf-8

import urllib
import json

from os.path import join
from slugify import slugify

from django.core.management.base import BaseCommand
from import_parltrack.utils import parse_dossier_data

PARLTRACK_URL = 'http://parltrack.euwiki.org/dossier/%s?format=json'

class Command(BaseCommand):
    """
    Import a Dossier from parltrack and save it in the
    representatives_votes model format
    """

    def handle(self, *args, **options):
        dossier_id = unicode(args[0])        
        parltrack_url = PARLTRACK_URL % dossier_id

        json_dump_localization = join("/tmp", "dossier_%s.json" % slugify(dossier_id))
        # print json_dump_localization

        urllib.urlretrieve(parltrack_url, json_dump_localization)

        dossier_data = json.load(open(json_dump_localization))
        parse_dossier_data(dossier_data, False)
