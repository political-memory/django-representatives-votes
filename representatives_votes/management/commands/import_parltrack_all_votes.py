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

        print "import proposals"

        try:
            with open(json_file) as json_data_file:
                bar = pyprind.ProgBar(get_number_of_votes())
                for i, vote_data in enumerate(ijson.items(json_data_file, 'item')):
                    if options['continue'] and i < self.cache.get('vote_data_number', 0):
                        continue
                    proposal, _ = self.parse_vote_data(vote_data)
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
        dossier_ref = vote_data.get('epref', '')
        dossier_title = vote_data.get('eptitle', '')
        proposal_display = '{} ({})'.format(vote_data['title'].encode('utf-8'), vote_data.get('report', '').encode('utf-8'))

        if not dossier_ref:
            logger.warning('No dossier for proposal {}'.format(proposal_display))
            dossier_title = vote_data['title']
            dossier_ref = vote_data.get('report', '')

        dossier, created = Dossier.objects.get_or_create(
            reference=dossier_ref
        )

        if created:
            # Try to find dossier title (only for new dossiers)
            if not dossier_title:
                # Fall back on parltrack dossier data
                dossier_title = self.get_dossier_title(dossier_ref)
                if not dossier_title:
                    logger.warning('No dossier title for proposal {}'.format(proposal_display))
                    dossier_title = vote_data['title']

            dossier.title = dossier_title
            dossier.link = 'http://www.europarl.europa.eu/oeil/popups/ficheprocedure.do?reference=%s' % dossier_ref
            dossier.save()

        logger.info("\nParsing proposal {}".format(proposal_display))
        logger.info("For dossier {} ({})".format(dossier.title.encode('utf-8'), dossier_ref.encode('utf-8')))

        return self.parse_proposal_data(
            proposal_data=vote_data,
            dossier=dossier
        )

    @transaction.atomic
    def parse_proposal_data(self, proposal_data, dossier):
        """Get or Create a proposal model from raw data"""
        proposal_display = '{} ({})'.format(proposal_data['title'].encode('utf-8'), proposal_data.get('report', '').encode('utf-8'))

        # Should remove this test when parltrack is fixed
        try:
            proposal, created = Proposal.objects.get_or_create(
                dossier=dossier,
                title=proposal_data['title'],
                reference=proposal_data.get('report'),
                datetime=_parse_date(proposal_data['ts']),
                kind=proposal_data.get('issue_type'),
                total_for=int(proposal_data.get('For', {}).get('total', 0)),
                total_abstain=int(proposal_data.get('Abstain', {}).get('total', 0)),
                total_against=int(proposal_data.get('Against', {}).get('total', 0))
            )
        except Exception as e:
            logger.warning("Can't import proposal {}".format(proposal_display))
            logger.warning("Exception({})".format(e))
            return (None, None)
        else:
            logger.debug("Proposal successfuly imported")

        # We dont import votes if proposal already exists
        if not created:
            logger.info('Return existing proposal {}'.format(proposal_display))
            return (proposal, False)

        positions = ['For', 'Abstain', 'Against']
        logger.info('Looking for votes in proposal {}'.format(proposal_display))
        for position in positions:
            for group_vote_data in proposal_data.get(position, {}).get('groups', {}):
                group_name = group_vote_data['group']
                for vote_data in group_vote_data['votes']:
                    if 'orig' in vote_data:
                        representative_name = vote_data['orig']
                    elif 'name' in vote_data:
                        representative_name = vote_data['name']
                    else:
                        representative_name = vote_data

                    if not isinstance(representative_name, unicode):
                        logger.warning("Can't import proposal {}".format(proposal_data.get('report', '').encode('utf-8')))
                        logger.warning("Representative not a str {}".format(representative_name))
                        return (None, None)

                    representative = self.get_representative(
                        representative_name, proposal.datetime.date(), group_name
                    )

                    representative_name_group = '{} ({})'.format(representative_name.encode('utf-8'), group_name.encode('utf-8'))

                    if representative:
                        Vote.objects.create(
                            proposal=proposal,
                            representative_id=representative,
                            representative_name=representative_name_group,
                            position=position.lower()
                        )
                    else:
                        # Despite all efforts we can not find a matching
                        # representative in db or parltrack
                        Vote.objects.create(
                            proposal=proposal,
                            representative=None,
                            representative_name=representative_name_group,
                            position=position.lower()
                        )

        return (proposal, True)

    def get_dossier_title(self, dossier_ref):
        """Fall back on parltrack for dossier data
        """
        logger.debug('Get dossier title from parltrack')
        url = 'http://parltrack.euwiki.org/dossier/%s?format=json' % dossier_ref
        json_file = urlopen(url).read()
        try:
            dossier_json = json.loads(json_file)
        except ValueError:
            logging.warning("Failed to get dossier on parltrack !")
            logging.warning('{}'.format(dossier_ref.encode('utf-8')))
            return None

        return dossier_json['procedure']['title']

    def get_representative(self, mep, vote_date, representative_group):
        """
        Find representative remote id from its name, the vote date and the representative group
        it uses the internal db, and if we don’t find him we use the parltrack site
        """
        # Only select representatives that have a country mandate at the vote date
        def representative_filter(**args):
            mandates = Mandate.objects.select_related('representative').filter(
                group__kind='country',
                begin_date__lte=vote_date,
                end_date__gte=vote_date,
                **args
            )

            return [mandate.representative for mandate in mandates]

        mep = mep.replace(u"ß", "SS")
        mep = mep.replace("(The Earl of) ", "")

        representative = representative_filter(representative__last_name__iexact=mep)
        if not representative:
            representative = representative_filter(representative__last_name__iexact=re.sub("^DE ", "", mep.upper()))
        if not representative:
            representative = representative_filter(representative__last_name__contains=mep.upper())
        if not representative:
            representative = representative_filter(representative__full_name__contains=re.sub("^MC", "Mc", mep.upper()))
        if not representative:
            representative = representative_filter(representative__full_name__icontains=mep)
        # if not representative:
            # representative = representative_filter(representative__slug__endswith=slugify(mep))

        if representative:
            # TODO Ugly hack, we should handle cases where there are multiple results
            representative = representative[0]
            return representative.pk

        mep_display = u'%s %s' % (mep, representative_group)
        self.cache['groups'].setdefault(representative_group, {})

        if mep in self.cache['groups'][representative_group].keys():
            return self.cache['groups'][representative_group][mep]

        url = 'http://parltrack.euwiki.org/mep/%s?format=json' % smart_str(mep)

        logger.info(u'Looking for mep %s on parltrack %s', mep_display, url)

        json_file = urlopen(url).read()

        try:
            mep_ep_json = json.loads(json_file)
        except ValueError:
            logger.warning('Failed to get mep on parltrack : %s' % mep_display)
            self.cache['groups'][representative_group][mep] = None
            return None

        mep_remote_id = mep_ep_json['UserID']
        representative = Representative.objects.filter(
            remote_id=mep_remote_id
        ).values_list('id', flat=True)[0]
        if representative_group not in self.cache['groups'].keys():
             self.cache['groups'][representative_group] = {}
        self.cache['groups'][representative_group][mep] = representative
        return representative

def get_number_of_votes():
    response = urlopen('http://parltrack.euwiki.org/')
    htmlparser = etree.HTMLParser()
    tree = etree.parse(response, htmlparser)
    e = tree.xpath(".//*[@id='stats']/ul/li[3]")[0]
    return e.text.split(' ')[-1]


def retrieve_xz_json(url, destination):
    "Download and extract json file from parltrack"

    if os.system("which unxz > /dev/null") != 0:
        raise Exception("XZ binary missing, please install xz")

    if os.path.exists(destination + '.hash'):
        with open(destination + '.hash', 'r') as f:
            etag = f.read()
    else:
        etag = False

    print "download lastest data dump of votes from parltrack"
    request = urlopen(url)
    request_etag = request.info()['ETag']

    if not etag or not etag == request_etag:

        if os.path.exists(destination + '.xz'):
            print "Clean old downloaded files"
            os.remove(destination + '.xz')

        if os.path.exists(destination):
            os.remove(destination)

        print "Download vote data from parltrack"
        urlretrieve(url, destination + '.xz')

        with open(destination + '.hash', 'w+') as f:
            f.write(request_etag)

        print "unxz it"
        os.system("unxz %s" % destination + '.xz')
    return destination

