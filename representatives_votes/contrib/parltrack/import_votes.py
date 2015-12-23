# coding: utf-8
import logging
import sys
from os.path import join

import ijson
import django
from django.apps import apps

from .lib import VoteImportCommand, vote_signal

vote_pre_import = vote_signal


JSON_URL = 'http://parltrack.euwiki.org/dumps/ep_votes.json.xz'
DESTINATION = join('/tmp', 'ep_votes.json')


def main(stream=None):
    if not apps.ready:
        django.setup()

    logger = logging.getLogger(__name__)

    command = VoteImportCommand(logger)
    command.init_cache()

    for vote_data in ijson.items(stream or sys.stdin, 'item'):
        command.parse_vote_data(vote_data)
