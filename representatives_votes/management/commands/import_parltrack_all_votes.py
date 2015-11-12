# coding: utf-8

# This file is part of django-parltrack-votes.
#
# django-parltrack-votes-data is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or any later version.
#
# django-parltrack-votes-data is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU General Affero Public
# License along with django-parltrack-votes.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2013 Laurent Peuch <cortex@worlddomination.be>
# Copyright (c) 2015 Arnaud Fabre <af@laquadrature.net>

import json
import os
import logging
import ijson
import re
import pyprind

from urllib import urlopen, urlretrieve
from lxml import etree

try:
    import cPickle as pickle
except ImportError:
    import pickle

from os.path import join

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils.encoding import smart_str
from django.db import transaction

from representatives.management.parltrack import retrieve_xz_json

# DateTime tools
from django.utils.timezone import make_aware as date_make_aware
from dateutil.parser import parse as date_parse
from pytz import timezone as date_timezone
from optparse import make_option

from representatives.models import Mandate, Representative
from representatives_votes.models import Dossier, Proposal, Vote

logger = logging.getLogger(__name__)

def _parse_date(date_str):
    return date_make_aware(date_parse(date_str), date_timezone('Europe/Brussels'))

JSON_URL = 'http://parltrack.euwiki.org/dumps/ep_votes.json.xz'
DESTINATION = join('/tmp', 'ep_votes.json')


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--continue',
                    action='store_true',
                    dest='continue',
                    default=False,
                    help='Continue where it failed'),
        make_option('--purge',
                    action='store_true',
                    dest='purge',
                    default=False,
                    help='Purge dossier before import'),
        make_option('--log',
                    action='store',
                    dest='loglevel',
                    default='WARNING',
                    help='Log lever (CRITICAL, ERROR, WARNING, INFO, DEBUG)'),
        )

    def handle(self, *args, **options):
        if options['purge']:
            Dossier.objects.all().delete()

        numeric_level = getattr(logging, options['loglevel'].upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError('Invalid log level: %s' % options['loglevel'])
        logging.basicConfig(level=numeric_level)

        json_file = retrieve_xz_json(JSON_URL, DESTINATION)

        print "read file", json_file

        self.cache = dict(groups={})
        self.cache_path = os.path.join(settings.DATA_DIR,
                'representative_finder.pickle')

        if os.path.exists(self.cache_path):
            with open(self.cache_path, 'r') as f:
                self.cache = pickle.load(f)

        self.index_representatives()
        self.index_dossiers()

        print "import proposals"

        try:
            with open(json_file) as json_data_file:
                bar = pyprind.ProgBar(get_number_of_votes())
                for i, vote_data in enumerate(ijson.items(json_data_file, 'item')):
                    if options['continue'] and i < self.cache.get('vote_data_number', 0):
                        continue

                    proposal = self.parse_vote_data(vote_data)

                    if proposal:
                        proposal_id = '{} - {} - {}'.format(i, proposal.dossier.title.encode('utf-8'), proposal.title.encode('utf-8'))
                    else:
                        proposal_id = None
                    self.cache['vote_data_number'] = i
                    bar.update(item_id = proposal_id)
                print(bar)
        except:
            self.save_cache()
            raise

        self.save_cache()

    def save_cache(self):
        with open(self.cache_path, 'w+') as f:
            pickle.dump(self.cache, f)

    def parse_vote_data(self, vote_data):
        """
        Parse data from parltrack votes db dumps (1 proposal)
        """
        if 'epref' not in vote_data.keys():
            logger.error('Could not import data without epref %s', vote_data)
            return

        dossier_pk = self.get_dossier(vote_data['epref'])

        if not dossier_pk:
            logger.info('Cannot find dossier with remote id %s',
                    vote_data['epref'])
            return

        return self.parse_proposal_data(
            proposal_data=vote_data,
            dossier_pk=dossier_pk
        )

    @transaction.atomic
    def parse_proposal_data(self, proposal_data, dossier_pk):
        """Get or Create a proposal model from raw data"""
        proposal_display = '{} ({})'.format(proposal_data['title'].encode('utf-8'), proposal_data.get('report', '').encode('utf-8'))

        if 'issue_type' not in proposal_data.keys():
            logger.error('This proposal data without issue_type: %s, %s',
                    proposal_data['epref'], proposal_data)
            return

        changed = False
        try:
            proposal = Proposal.objects.get(dossier_id=dossier_pk,
                    reference=proposal_data.get('report'),
                    kind=proposal_data.get('issue_type'))
        except Proposal.DoesNotExist:
            proposal = Proposal(dossier_id=dossier_pk,
                    reference=proposal_data.get('report'),
                    kind=proposal_data.get('issue_type'))
            changed = True

        data_map = dict(
            title=proposal_data['title'],
            datetime=_parse_date(proposal_data['ts']),
        )

        for position in ('For', 'Abstain', 'Against'):
            position_data = proposal_data.get(position, {})
            position_total = position_data.get('total', 0)

            try:
                position_total = int(position_total)
            except ValueError:
                position_total = 0


            data_map['total_%s' % position.lower()] = position_total

        for key, value in data_map.items():
            if value != getattr(proposal, key, None):
                setattr(proposal, key, value)
                changed = True

        votes = proposal.votes.all() if proposal.pk else []

        if changed:
            proposal.save()

        positions = ['For', 'Abstain', 'Against']
        logger.info('Looking for votes in proposal {}'.format(proposal_display))
        for position in positions:
            for group_vote_data in proposal_data.get(position, {}).get('groups', {}):
                group_name = group_vote_data['group']
                for vote_data in group_vote_data['votes']:
                    if not isinstance(vote_data, dict):
                        logger.error('Skipping vote data %s for proposal %s',
                                vote_data, proposal_data['_id'])
                        continue

                    try:
                        representative_pk = self.get_representative(
                                vote_data['id'])
                        representative_name = vote_data['orig']
                    except KeyError:
                        logger.error('Skipping vote data %s for proposal %s',
                                vote_data, proposal_data['_id'])
                        continue

                    found = False
                    for vote in votes:
                        if (representative_pk is not None
                                and representative_pk == vote.representative_id):

                            found = True
                            break

                        elif (representative_pk is None
                                and vote.representative_name == representative_name):
                            found = True
                            break

                    changed = False
                    if not found:
                        vote = Vote(proposal_id=proposal.pk,
                                representative_id=representative_pk,
                                representative_name=representative_name)

                        changed = True

                    if vote.position != position.lower():
                        changed = True
                        vote.position = position.lower()

                    if changed:
                        vote.save()

        return proposal

    def index_dossiers(self):
        self.cache['dossiers'] = {
            d[0]: d[1] for d in Dossier.objects.values_list('reference', 'pk')
        }

    def get_dossier(self, reference):
        return self.cache['dossiers'].get(reference, None)

    def index_representatives(self):
        self.cache['meps'] = {l[0]: l[1] for l in
                Representative.objects.values_list('remote_id', 'pk')}

    def get_representative(self, mep):
        return self.cache['meps'].get(mep, None)


def get_number_of_votes():
    response = urlopen('http://parltrack.euwiki.org/')
    htmlparser = etree.HTMLParser()
    tree = etree.parse(response, htmlparser)
    e = tree.xpath(".//*[@id='stats']/ul/li[3]")[0]
    return e.text.split(' ')[-1]
