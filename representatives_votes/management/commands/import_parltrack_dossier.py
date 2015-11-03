# coding: utf-8

import urllib
import json

from os.path import join
from slugify import slugify

from django.core.management.base import BaseCommand
from import_parltrack_votes.utils import parse_dossier_data

PARLTRACK_URL = 'http://parltrack.euwiki.org/dossier/{}?format=json'

def parse_dossier_data(dossier_data):
    """Parse data from parltarck dossier export (1 dossier) Update dossier
    if it existed before, this function goal is to import and update a
    dossier, not to import all parltrack data
    """

    dossier, created = Dossier.objects.get_or_create(
        reference=dossier_data['procedure']['reference'],
    )

    dossier.title = dossier_data['procedure']['title']
    dossier.link = dossier_data['meta']['source']
    dossier.save()

    logger.info('Dossier: ' + dossier.title.encode('utf-8'))

    # previous_proposals = set(dossier.proposals.all())
    for proposal_data in dossier_data['votes']:
        proposal, created = parse_proposal_data(
            proposal_data,
            dossier
        )
        # if not created:
            # previous_proposals.remove(proposal)

    # Delete proposals that dont belongs to this dossier anymore
    # for proposal in previous_proposals:
        # proposal.delete()

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
