# coding: utf-8



def find_matching_mep_in_db(mep, vote_date, mep_group):
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
