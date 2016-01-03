# coding: utf-8

import logging
import sys

import ijson
import django
from django.apps import apps

from .lib import parse_dossier_data


def run(stream, logger):
    for data in ijson.items(stream, ''):
        parse_dossier_data(data, logger)


def main(stream=None):
    if not apps.ready:
        django.setup()

    run(stream or sys.stdin, logging.getLogger(__name__))
