# coding: utf-8

import logging
import sys

import ijson
import django
from django.apps import apps

from .lib import parse_dossier_data

URL = 'http://parltrack.euwiki.org/dumps/ep_dossiers.json.xz'
LOCAL_PATH = 'ep_dossiers.json.xz'


def main(stream=None):
    if not apps.ready:
        django.setup()

    logger = logging.getLogger(__name__)

    for data in ijson.items(stream or sys.stdin, 'item'):
        parse_dossier_data(data, logger)
