# coding: utf-8

"""
Fix for ugly data from Parltrack
"""

import re
import json

from urllib import urlopen
# from slugify import slugify

from representatives.models import Mandate, Representative

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
    
    print 'WARNING: failed to get mep using internal db, fall back on parltrack'
    print "http://parltrack.euwiki.org/mep/%s?format=json" % (mep.encode("Utf-8"))
    mep_ep_id = json.loads(urlopen("http://parltrack.euwiki.org/mep/%s?format=json" % (mep.encode("Utf-8"))).read())["UserID"]
    print mep_ep_id, mep,
    print json.loads(urlopen("http://parltrack.euwiki.org/mep/%s?format=json" % (mep.encode("Utf-8"))).read())["Name"]["full"]

    representative = Representative.objects.get(remote_id=mep_ep_id)
    return representative

