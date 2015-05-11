# coding: utf-8

import urllib
import json

from datetime import datetime

from os.path import join
from slugify import slugify

from django.core.management.base import BaseCommand
from representatives_votes.models import Dossier, Proposal, Vote
# from representatives.models import Representative
import import_parltrack.utils as utils

PARLTRACK_URL = 'http://parltrack.euwiki.org/dossier/%s?format=json'

_parse_date = lambda date: datetime.strptime(date, "%Y-%m-%dT%H:%M:%S")

class Command(BaseCommand):
    """
    Import a Dossier from parltrack and save it in the
    representatives_votes model format
    """
    def add_arguments(self, parser):
        parser.add_argument('dossier_id', nargs=1, type=str)

    def parse_json_dossier_data(self, dossier_data):
        
        dossier, created = Dossier.objects.get_or_create(reference=dossier_data['procedure']['reference'])
        dossier.title = dossier_data['procedure']['title']
        dossier.link = dossier_data['meta']['source'] 
        dossier.save()

        Vote.objects.filter(proposal__dossier=dossier).delete()
        Proposal.objects.filter(dossier=dossier).delete()
        
        for proposal_data in dossier_data['votes']:
            proposal = Proposal.objects.create(
                dossier=dossier,
                title=proposal_data['title'],
                reference=proposal_data['report'],
                datetime=_parse_date(proposal_data['ts']),
                total_for=int(proposal_data['For']['total']),
                total_abstain=int(proposal_data['Abstain']['total']),
                total_against=int(proposal_data['Against']['total'])
            )

            positions = ['For', 'Abstain', 'Against']
            for position in positions:
                for group_vote_data in proposal_data[position]['groups']:
                    group_name = group_vote_data['group']
                    for vote_data in group_vote_data['votes']:
                        for mep in vote_data:                        
                            representative = utils.find_matching_representatives_in_db(
                                vote_data['orig'], proposal.datetime, group_name)
                            Vote.objects.create(
                                proposal=proposal,
                                representative_remote_id=representative.remote_id,
                                position=position.lower()
                            )
                            
    def handle(self, *args, **options):
        dossier_id = unicode(args[0])        
        parltrack_url = PARLTRACK_URL % dossier_id

        json_dump_localization = join("/tmp", "dossier_%s.json" % slugify(dossier_id))
        # print json_dump_localization

        urllib.urlretrieve(parltrack_url, json_dump_localization)

        dossier_data = json.load(open(json_dump_localization))
        self.parse_json_dossier_data(dossier_data)
