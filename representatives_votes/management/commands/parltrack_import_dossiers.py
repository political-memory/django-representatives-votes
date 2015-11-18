# coding: utf-8
import logging
import gc
import fileinput
import os
import urllib
import json
import ijson

from django.core.management.base import BaseCommand

from representatives.management.parltrack import retrieve_xz_json
from representatives_votes.models import Dossier

logger = logging.getLogger(__name__)

URL = 'http://parltrack.euwiki.org/dumps/ep_dossiers.json.xz'
LOCAL_PATH = 'ep_dossiers.json.xz'


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
    Import Dossiers from parltrack.
    """

    def handle(self, *args, **options):
        path = retrieve_xz_json(URL, LOCAL_PATH)

        with open(path, 'r') as f:
            for dossier in ijson.items(f, 'item'):
                parse_dossier_data(dossier)


def main():
    import django
    django.setup()

    i = 0
    for line in fileinput.input():
        i += 1

        # Fix first line
        line = line.lstrip('[')
        # Fix last line
        line = line.lstrip(']')
        # Skip inter-line
        if line.strip() in ('', ','):
            continue

        try:
            dossier = json.loads(line)
        except:
            logger.error(u'Error parsing line %s' % i)
        else:
            logger.debug(u'Processing dossier %s',
                    dossier.get('epref', dossier))

            parse_dossier_data(dossier)

        if not i % 100:
            aoeu
            print '---------------------------------------------------------------------------------'
            gc.collect()
            i = 0
