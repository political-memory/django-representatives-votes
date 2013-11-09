import os
import sys
import pytz
import urllib
from os.path import join
from datetime import datetime

import ijson
from dateutil.parser import parse

from django.core.management.base import BaseCommand
from django.db import transaction, reset_queries
from django.utils.timezone import make_aware

from representatives.models import Representative
from representatives_votes.models import Proposal, ProposalPart, Vote


class Command(BaseCommand):
    args = '<option file>'
    help = 'Import vote of the ep parliaments'

    def handle(self, *args, **options):
        if args:
            json_file = args[0]
        else:
            json_file = retrieve_json()

        print "read file", json_file
        start = datetime.now()
        with transaction.commit_on_success():
            vote_iter = ijson.items(open(json_file), 'item')
            for i, vote in enumerate(vote_iter):
                create_in_db(vote)
                reset_queries()  # to avoid memleaks in debug mode
                sys.stdout.write("%s\r" % i)
                sys.stdout.flush()
        sys.stdout.write("\n")
        print datetime.now() - start


def parse_date(date):
    return make_aware(parse(date), pytz.timezone("Europe/Brussels"))


def create_in_db(vote):
    #cur = connection.cursor()
    #proposal_name = vote.get("report", vote["title"])

    proposal = Proposal.objects.filter(code_name=vote["code_name"])
    if not proposal:
        proposal = Proposal.objects.create(
            title=vote['title'],
            date=vote['date'],
            code_name=vote['code_name']
        )
    else:
        proposal = proposal[0]

    for part in vote['parts']:
        proposal_part = ProposalPart.objects.filter(
            datetime=make_aware(datetime.fromtimestamp(int(part['datetime']) / 1000), pytz.timezone("Europe/Brussels")),
            subject=part['part'],
            part=part['subject'],
            #description=part[''],
            proposal=proposal,
        )
        if not proposal_part:
            proposal_part = ProposalPart.objects.create(
            datetime=make_aware(datetime.fromtimestamp(int(part['datetime']) / 1000), pytz.timezone("Europe/Brussels")),
            subject=part['part'],
            part=part['subject'],
            #description=part[''],
            proposal=proposal,
        )
        else:
            proposal_part = proposal_part[0]

        for choice in ('for', 'against', 'abstention'):
            for mep_id in part.get('votes_%s' % choice, []):
                if not Representative.objects.filter(remote_id=mep_id):
                    continue
                mep = Representative.objects.get(remote_id=mep_id)
                vote = Vote.objects.filter(
                    choice=choice,
                    representative=mep,
                    proposal_part=proposal_part,
                )
                if not vote:
                    vote = Vote.objects.create(
                        choice=choice,
                        representative=mep,
                        proposal_part=proposal_part,
                    )


def retrieve_json():
    "Download and extract json file from toutatis"
    print "Clean old downloaded files"
    json_file = join("/tmp", "ep_votes.json")
    if os.path.exists(json_file):
        os.remove(json_file)
    print "Download vote data from toutatis"
    urllib.urlretrieve('http://toutatis.mm.staz.be/latest/', json_file)
    return json_file
