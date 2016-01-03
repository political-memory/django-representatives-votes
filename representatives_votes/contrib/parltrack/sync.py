# coding: utf-8

import logging
import urllib2

from . import import_single_dossier

BASE_URL = 'http://parltrack.euwiki.org'


def sync_dossier(reference):
    logger = logging.getLogger(__name__)
    url = '%s/dossier/%s?format=json' % (BASE_URL, reference)

    logger.debug('Syncing dossier from %s' % url)
    import_single_dossier.run(urllib2.urlopen(url), logger)
