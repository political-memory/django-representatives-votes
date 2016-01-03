# coding: utf-8

import urllib2


class ParltrackDataSource:
    base_url = 'http://parltrack.euwiki.org'

    def dossier(self, reference):
        url = '%s/dossier/%s?format=json' % (self.base_url, reference)
        return urllib2.urlopen(url)
