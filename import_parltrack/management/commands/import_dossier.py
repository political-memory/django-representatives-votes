# coding: utf-8

import urllib
import json

from os.path import join
from slugify import slugify
from pprint import pprint

from django.core.management.base import BaseCommand

from representatives_votes.models import Dossier, Proposal, Vote
from representatives.models import Representative
import parltrack_votes.utils as utils

PARLTRACK_URL = 'http://parltrack.euwiki.org/dossier/%s?format=json'


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('dossier_id', nargs=1, type=str)

    def handle(self, *args, **options):
        dossier_id = unicode(args[0])        
        parltrack_url = PARLTRACK_URL % dossier_id

        json_dump_localization = join("/tmp", "dossier_%s.json" % slugify(dossier_id))
        # print json_dump_localization

        urllib.urlretrieve(parltrack_url, json_dump_localization)

        dossier_data = json.load(open(json_dump_localization))

        dossier, created = Dossier.objects.get_or_create(reference=dossier_data['procedure']['reference'])

        dossier.title = dossier_data['procedure']['title']
        dossier.link = dossier_data['meta']['source']

        dossier.save()

        for proposal_data in dossier_data['votes']:
            proposal = Proposal()
            proposal.dossier = dossier
            proposal.title = proposal_data['title']
            proposal.reference = proposal_data['report']
            proposal.date = proposal_data['ts']

            proposal.total_for = int(proposal_data['For']['total'])
            proposal.total_abstain = int(proposal_data['Abstain']['total'])
            proposal.total_against = int(proposal_data['Against']['total'])
            
            print(proposal.__dict__)
            
            for group_vote_data in proposal_data['For']['groups']:
                group_name = group_vote_data['group']
                print(group_name)
                for vote_data in group_vote_data['votes']:
                    for mep in vote_data:
                        print(vote_data['orig'])
                        
                
            # print(proposal.__dict__)
            # print(proposal_data.keys())
            # print(proposal_data['For'])

        # utils.find_matching_mep_in_db('test', 'test 2')
        # print(dossier['votes'])
        
        # pprint(dossier['votes'])
        # pprint(dossier['meta'])
        # pprint(dossier['procedure'])
