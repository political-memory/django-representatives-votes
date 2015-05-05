# -*- coding:Utf-8 -*-
import re
from functools import partial


from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from parltrack_meps.models import MEP, CountryMEP
from parltrack_votes.models import ProposalPart


class Command(BaseCommand):
    help = 'Create a voting recommandation, WARNING: due to the nature of the data, there is sadly non-negligible chances that this command will fail'
    args= "<proposal_part_id>"

    def handle(self, *args, **options):
        if not args:
            raise CommandError("Usage: %s <proposal_part id>" % __file__)

        proposal_part_id = args[0]
        with transaction.commit_on_success():
            link_mep(proposal_part_id)


def link_mep(proposal_part_id):
    proposal_part = ProposalPart.objects.get(id=proposal_part_id)
    for vote in proposal_part.vote_set.all():
        vote.mep = find_matching_mep_in_db(vote.raw_mep, vote.proposal_part.datetime)
        vote.save()

def find_matching_mep_in_db(mep, vote_date):
    def mep_filter(**args):
        return  [cm.mep for cm in CountryMEP.objects.select_related('mep').filter(begin__lt=vote_date, end__gt=vote_date, **args)]

    mep = mep.replace(u"ß", "SS")
    mep = mep.replace("(The Earl of) ", "")

    representative = mep_filter(mep__last_name=mep)
    if not representative:
        representative = mep_filter(mep__last_name__iexact=mep)
    if not representative:
        representative = mep_filter(mep__last_name__iexact=re.sub("^DE ", "", mep.upper()))
    if not representative:
        representative = mep_filter(mep__last_name__contains=mep.upper())
    if not representative:
        representative = mep_filter(mep__full_name__contains=re.sub("^MC", "Mc", mep.upper()))
    if not representative:
        representative = mep_filter(mep__full_name__icontains=mep)

    if representative:
        return representative[0]

    print "WARNING: failed to get mep using internal db, fall back on parltrack"
    print "http://parltrack.euwiki.org/mep/%s?format=json" % (mep.encode("Utf-8"))
    mep_ep_id = json.loads(urlopen("http://parltrack.euwiki.org/mep/%s?format=json" % (mep.encode("Utf-8"))).read())["UserID"]
    print mep_ep_id, mep, json.loads(urlopen("http://parltrack.euwiki.org/mep/%s?format=json" % (mep.encode("Utf-8"))).read())["Name"]["full"]
    representative = MEP.objects.get(ep_id=mep_ep_id).representative_ptr
    return representative


# vim:set shiftwidth=4 tabstop=4 expandtab:
