# coding: utf-8

import logging

from . import import_single_dossier
from .datasource import ParltrackDataSource


def sync_dossier(reference, source=None):
    if source is None:
        source = ParltrackDataSource()

    logger = logging.getLogger(__name__)
    import_single_dossier.run(source.dossier(reference), logger)
