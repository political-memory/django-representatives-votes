# coding: utf-8
from __future__ import print_function

import re
import json
import functools
import sys

# DateTime tools
from django.utils.timezone import make_aware as date_make_aware
from dateutil.parser import parse as date_parse
from pytz import timezone as date_timezone

from django.db import transaction

from urllib import urlopen

from representatives.models import Mandate
from representatives_votes.models import Dossier, Proposal, Vote
from import_parltrack_votes.models import Matching

def _parse_date(date_str):
    return date_make_aware(date_parse(date_str), date_timezone('Europe/Brussels'))

def parse_dossier_data(dossier_data, skip_old = True):
    """
    Parse data from parltarck dossier export (1 dossier)
    """

    dossier, created = Dossier.objects.get_or_create(
        reference=dossier_data['procedure']['reference'],
    )
    
    if skip_old and not created:
        return
    
    dossier.title = dossier_data['procedure']['title']
    dossier.link = dossier_data['meta']['source']
    dossier.save()
    
    print('Dossier: ' + dossier.title.encode('utf-8'))

    Vote.objects.filter(proposal__dossier=dossier).delete()
    Proposal.objects.filter(dossier=dossier).delete()
    
    for proposal_data in dossier_data['votes']:
        parse_proposal_data(
            proposal_data,
            dossier,
            skip_old=skip_old
        )

def parse_vote_data(vote_data, skip_old = True):
    '''
    Parse data from parltrack votes db dumps (1 proposal)
    '''
    dossier_ref = vote_data.get('epref', '')
    dossier_title = vote_data.get('eptitle', '')
    proposal_display = '%s (%s)' % (vote_data['title'].encode('utf-8'), vote_data.get('report', '').encode('utf-8'))
    
    if not dossier_ref:
        print('No dossier for proposal %s' % proposal_display)
        dossier_title = vote_data['title']
        dossier_ref = vote_data.get('report', '')

    dossier, created = Dossier.objects.get_or_create(
        reference=dossier_ref
    )
    
    if created:
        # Try to find dossier title (only for new dossiers)
        if not dossier_title:
            # Fall back on parltrack dossier data
            dossier_title = get_dossier_title(dossier_ref)
            if not dossier_title:
                print('No dossier title for proposal %s' % proposal_display)
                dossier_title = vote_data['title']

        dossier.title = dossier_title
        dossier.link = 'http://www.europarl.europa.eu/oeil/popups/ficheprocedure.do?reference=%s' % dossier_ref
        dossier.save()

    print("\nDossier: %s (%s)" % (dossier.title.encode('utf-8'), dossier_ref.encode('utf-8')))

    return parse_proposal_data(
        proposal_data=vote_data,
        dossier=dossier,
        skip_old=skip_old
    )


def get_dossier_title(dossier_ref):
    '''
    Fall back on parltrack for dossier data
    '''

    url = 'http://parltrack.euwiki.org/dossier/%s?format=json' % dossier_ref
    json_file = urlopen(url).read()
    try:
        dossier_json = json.loads(json_file)
    except ValueError:
        print("⚠ WARNING: failed to get dossier on parltrack !")
        print('%s' % dossier_ref.encode('utf-8'))
        return None

    return dossier_json['procedure']['title']


@transaction.atomic
def parse_proposal_data(proposal_data, dossier, skip_old = True):
    '''Get or Create a proposal model from raw data'''

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
    except ValueError:
        print("Can't import proposal %s" % (proposal_data.get('report', '').encode('utf-8')), file=sys.stderr)
        return None

    print('Proposal: ' + proposal.title.encode('utf-8'))
    
    if skip_old and not created:
        return (proposal, False)

    positions = ['For', 'Abstain', 'Against']
    for position in positions:
        for group_vote_data in proposal_data.get(position, {}).get('groups', {}):
            group_name = group_vote_data['group']
            for vote_data in group_vote_data['votes']:
                if 'orig' in vote_data:
                    representative_name = vote_data['orig']
                else:
                    representative_name = vote_data

                if not isinstance(representative_name, unicode):
                    print("Can't import proposal %s" % (proposal_data.get('report', '').encode('utf-8')), file=sys.stderr)
                    return None

                representative_id = find_matching_representatives_in_db(
                    representative_name, proposal.datetime.date(), group_name
                )

                representative_name_group = '%s (%s)' % (representative_name, group_name)
                
                if representative_id:
                    Vote.objects.create(
                        proposal=proposal,
                        representative_remote_id=representative_id,
                        representative_name=representative_name_group,
                        position=position.lower()
                    )
                else:
                    # Despite all efforts we can not find a matching
                    # representative in db or parltrack
                    Vote.objects.create(
                        proposal=proposal,
                        representative_remote_id=None,
                        position=position.lower(),
                        representative_name=representative_name_group
                    )
                
    return (proposal, True)


def memoize(obj):
    '''
    memoize decorator for keeping representative matches in cache
    '''
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        return cache[key]
    return memoizer

@memoize
def find_matching_representatives_in_db(mep, vote_date, representative_group):
    '''
    Find representative remote id from its name, the vote date and the representative group
    it uses the internal db, and if we don’t find him we use the parltrack site
    '''
    # Only select representatives that have a country mandate at the vote date
    def representative_filter(**args):
        mandates = Mandate.objects.select_related('representative').filter(
            group__kind='country',
            begin_date__lte=vote_date,
            end_date__gte=vote_date,
            **args
        )
        
        return [mandate.representative for mandate in mandates]

    if isinstance(mep, dict):
        print(mep)

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
        return representative.remote_id

    try:
        mep = mep.encode('utf-8')
        # Try by searching in the Matching table, avoid many conexions to parltrack
        matching = Matching.objects.get(mep_name=mep, mep_group=representative_group)
        return matching.representative_remote_id
    except Matching.DoesNotExist:
        mep_display = '%s (%s)' % (mep, representative_group.encode('utf-8'))
        # print("WARNING: failed to get mep using internal db, fall back on parltrack"),
        # print(mep_display)
        url = 'http://parltrack.euwiki.org/mep/%s?format=json' % mep
        
        json_file = urlopen(url).read()
        try:
            mep_ep_json = json.loads(json_file)
        except ValueError:
            print("⚠ WARNING: failed to get mep on parltrack !"),
            print(mep_display)
            Matching.objects.create(
                mep_name=mep,
                mep_group=representative_group,
                representative_remote_id=None
            )
            return None

        mep_remote_id = mep_ep_json['UserID']
        
        Matching.objects.create(
            mep_name=mep,
            mep_group=representative_group,
            representative_remote_id=mep_remote_id
        )
        return mep_remote_id
