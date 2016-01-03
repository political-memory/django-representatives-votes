# coding: utf-8

import django
import django.dispatch

from dateutil.parser import parse as date_parse
from django.db import transaction
from django.utils.timezone import make_aware as date_make_aware
from pytz import timezone as date_timezone

from representatives.models import Representative
from representatives_votes.models import Dossier, Proposal, Vote


vote_signal = django.dispatch.Signal(providing_args=['vote_data'])


def parse_dossier_data(data, logger):
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

    if 'votes' in data.keys() and 'epref' in data['votes']:
        command = VoteImportCommand(logger)
        command.init_cache()
        command.parse_vote_data(data['votes'])


def _parse_date(date_str):
    return date_make_aware(
        date_parse(date_str),
        date_timezone('Europe/Brussels'))


class VoteImportCommand(object):
    def __init__(self, logger):
        self.logger = logger

    def init_cache(self):
        self.cache = dict()
        self.index_representatives()
        self.index_dossiers()

    def parse_vote_data(self, vote_data):
        """
        Parse data from parltrack votes db dumps (1 proposal)
        """
        if 'epref' not in vote_data.keys():
            self.logger.debug('Could not import data without epref %s',
                vote_data['title'])
            return

        dossier_pk = self.get_dossier(vote_data['epref'])

        if not dossier_pk:
            self.logger.debug('Cannot find dossier with remote id %s',
                         vote_data['epref'])
            return

        return self.parse_proposal_data(
            proposal_data=vote_data,
            dossier_pk=dossier_pk
        )

    @transaction.atomic
    def parse_proposal_data(self, proposal_data, dossier_pk):
        """Get or Create a proposal model from raw data"""
        proposal_display = '{} ({})'.format(proposal_data['title'].encode(
            'utf-8'), proposal_data.get('report', '').encode('utf-8'))

        if 'issue_type' not in proposal_data.keys():
            self.logger.debug('This proposal data without issue_type: %s',
                         proposal_data['epref'])
            return

        changed = False
        try:
            proposal = Proposal.objects.get(title=proposal_data['title'])
        except Proposal.DoesNotExist:
            proposal = Proposal(title=proposal_data['title'])
            changed = True

        data_map = dict(
            title=proposal_data['title'],
            datetime=_parse_date(proposal_data['ts']),
            dossier_id=dossier_pk,
            reference=proposal_data.get('report'),
            kind=proposal_data.get('issue_type')
        )

        for position in ('For', 'Abstain', 'Against'):
            position_data = proposal_data.get(position, {})
            position_total = position_data.get('total', 0)

            if isinstance(position_total, str) and position_total.isdigit():
                position_total = int(position_total)

            data_map['total_%s' % position.lower()] = position_total

        for key, value in data_map.items():
            if value != getattr(proposal, key, None):
                setattr(proposal, key, value)
                changed = True

        if changed:
            proposal.save()

        responses = vote_signal.send(sender=self,
            vote_data=proposal_data)

        for receiver, response in responses:
            if response is False:
                self.logger.debug(
                    'Skipping dossier %s', proposal_data.get(
                        'epref', proposal_data['title']))
                return

        positions = ['For', 'Abstain', 'Against']
        self.logger.info(
            'Looking for votes in proposal {}'.format(proposal_display))
        for position in positions:
            for group_vote_data in proposal_data.get(
                    position,
                    {}).get(
                    'groups',
                    {}):
                for vote_data in group_vote_data['votes']:
                    if not isinstance(vote_data, dict):
                        self.logger.error(
                            'Skipping vote data %s for proposal %s',
                            vote_data, proposal_data['_id'])
                        continue

                    representative_pk = self.get_representative(vote_data)

                    if representative_pk is None:
                        self.logger.error(
                            'Could not find mep for %s',
                            vote_data)
                        continue

                    representative_name = vote_data.get('orig', '')

                    changed = False
                    try:
                        vote = Vote.objects.get(
                            representative_id=representative_pk,
                            proposal_id=proposal.pk)
                    except Vote.DoesNotExist:
                        vote = Vote(proposal_id=proposal.pk,
                            representative_id=representative_pk)
                        changed = True

                    if vote.position != position.lower():
                        changed = True
                        vote.position = position.lower()

                    if vote.representative_name != representative_name:
                        changed = True
                        vote.representative_name = representative_name

                    if changed:
                        vote.save()
                        self.logger.debug(
                            'Save vote %s for MEP %s on %s #%s to %s',
                            vote.pk, representative_pk, proposal_data['title'],
                            proposal.pk, position)

        return proposal

    def index_dossiers(self):
        self.cache['dossiers'] = {
            d[0]: d[1] for d in Dossier.objects.values_list('reference', 'pk')
        }

    def get_dossier(self, reference):
        return self.cache['dossiers'].get(reference, None)

    def index_representatives(self):
        self.cache['meps'] = {int(l[0]): l[1] for l in
            Representative.objects.values_list('remote_id', 'pk')}

    def get_representative(self, vote_data):
        if vote_data.get('ep_id', None) is None:
            return
        return self.cache['meps'].get(int(vote_data['ep_id']), None)
