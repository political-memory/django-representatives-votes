# coding: utf-8
import re
import json
import functools

from django.db import transaction

# DateTime tools
from django.utils.timezone import make_aware as date_make_aware
from dateutil.parser import parse as date_parse
from pytz import timezone as date_timezone

from urllib import urlopen

from representatives.models import Mandate, Representative
from representatives_votes.models import Dossier, Proposal, Vote

def _parse_date(date_str):
    return date_make_aware(date_parse(date_str), date_timezone('Europe/Brussels'))

@transaction.atomic
def parse_dossier_data(dossier_data, skip_old = True):
    """
    Parse data from parltarck dossier export
    """

    dossier, created = Dossier.objects.get_or_create(
        reference=dossier_data['procedure']['reference'],
    )
    
    if skip_old and not created:
        return
    
    dossier.title = dossier_data['procedure']['title']
    dossier.link = dossier_data['meta']['source'] 
    dossier.save()

    Vote.objects.filter(proposal__dossier=dossier).delete()
    Proposal.objects.filter(dossier=dossier).delete()

    for proposal_data in dossier_data['votes']:
        parse_proposal_data(proposal_data, dossier)

@transaction.atomic
def parse_vote_data(vote_data, skip_old = True):
    dossier_ref = vote_data.get('epref', '')
    dossier_title = vote_data.get('eptitle', '')
    
    if not dossier_title:
        # Fail back on parltrack dossier data
        if dossier_ref:
            dossier_title = get_dossier_title(dossier_ref)
            if not dossier_title:
                print('No dossier title for proposal %s (%s)' % (vote_data['title'], vote_data.get('report', '')))
                dossier_title = vote_data['title']
        else:
            print('No dossier for proposal %s (%s)' % (vote_data['title'], vote_data.get('report', '')))
            dossier_title = vote_data['title']
            dossier_ref = vote_data.get('report', '')
                
    dossier_link = 'http://www.europarl.europa.eu/oeil/popups/ficheprocedure.do?reference=%s' % dossier_ref
    
    dossier, created = Dossier.objects.get_or_create(
        title=dossier_title,
        reference=dossier_ref,
        link=dossier_link
    )

    return parse_proposal_data(
        proposal_data=vote_data,
        dossier=dossier,
        skip_old=skip_old
    )

def get_dossier_title(dossier_ref):
    """
    Fall back on parltrack for dossier data
    """
    url = 'http://parltrack.euwiki.org/dossier/%s?format=json' % dossier_ref
    json_file = urlopen(url).read()
    try:
        dossier_json = json.loads(json_file)
    except ValueError:
        print("⚠ WARNING: failed to get dossier on parltrack !")
        print('%s' % (dossier_ref))
        return None

    return dossier_json['procedure']['title']

@transaction.atomic
def parse_proposal_data(proposal_data, dossier, skip_old = True):
    """
    Get or Create a proposal model from raw data,
    return True if the 
    """
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
                
                representative = find_matching_representatives_in_db(
                    representative_name, proposal.datetime, group_name
                )
                if representative:
                    Vote.objects.create(
                        proposal=proposal,
                        representative_remote_id=representative.remote_id,
                        position=position.lower()
                    )
                else:
                    # Despite all efforts we can not find a matching
                    # representative in db or parltrack
                    representative_name = '%s (%s)' % (representative_name, group_name)
                    
                    Vote.objects.create(
                        proposal=proposal,
                        representative_remote_id=None,
                        position=position.lower(),
                        representative_name=representative_name
                    )
    return (proposal, True)

def find_matching_representatives_in_db(mep, vote_date, representative_group):        

    # Only select representatives that are on mandate during the vote
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
        return representative
    
    # print "WARNING: failed to get mep using internal db, fall back on parltrack"
    url = 'http://parltrack.euwiki.org/mep/%s?format=json' % (mep.encode('utf-8'))
    # print(url)
    
    json_file = urlopen(url).read()
    try:
        mep_ep_json = json.loads(json_file)
    except ValueError:
        print("⚠ WARNING: failed to get mep on parltrack !")
        print('%s (%s)' % (mep, representative_group))
        return None
    
    mep_ep_id = mep_ep_json['UserID']
    full_name = mep_ep_json['Name']['full']

    # print 'Found : "%s" (%d), for "%s"' % (full_name, mep_ep_id, mep)
    try:
        representative = Representative.objects.get(remote_id=mep_ep_id)
    except Representative.DoesNotExist:
        print("⚠ WARNING: failed to get mep on internal db but found on parltrack !")
        print('%s (%s)' % (mep, representative_group))
        return None
        
    return representative

