# coding: utf-8

import logging
import sys

import ijson
import django
from django.apps import apps

from .lib import parse_dossier_data


def main(stream=None):
    if not apps.ready:
        django.setup()

    logger = logging.getLogger(__name__)

    for data in ijson.items(stream or sys.stdin, ''):
        parse_dossier_data(data, logger)
