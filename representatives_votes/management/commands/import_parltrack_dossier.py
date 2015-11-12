# coding: utf-8

import urllib
import json
import logging

from os.path import join
from slugify import slugify

from django.core.management.base import BaseCommand

from representatives_votes.models import Dossier
from import_parltrack_votes.utils import parse_dossier_data

PARLTRACK_URL = 'http://parltrack.euwiki.org/dossier/{}?format=json'

logger = logging.getLogger(__name__)


def parse_dossier_data(data):
    """Parse data from parltarck dossier export (1 dossier) Update dossier
    if it existed before, this function goal is to import and update a
    dossier, not to import all parltrack data
    """
    changed = False
    ref = data['procedure']['reference']

    logger.debug('Processing dossier %s', ref)

    try:
        dossier = Dossier.objects.get(reference=ref)
    except Dossier.DoesNotExist:
        dossier = Dossier(reference=ref)
        logger.debug('Dossier did not exist')
        changed = True

    if dossier.title != data['procedure']['title']:
        logger.debug('Title changed from "%s" to "%s"', dossier.title,
                data['procedure']['title'])
        dossier.title = data['procedure']['title']
        changed = True

    source = data['meta']['source'].replace('&l=en', '')
    if dossier.link != source:
        logger.debug('Source changed from "%s" to "%s"', dossier.link, source)
        dossier.link = source
        changed = True

    if changed:
        logger.info('Updated dossier %s', ref)
        dossier.save()


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
