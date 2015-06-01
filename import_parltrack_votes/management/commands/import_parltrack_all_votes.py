# coding: utf-8

# This file is part of django-parltrack-votes.
#
# django-parltrack-votes-data is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of
# the License, or any later version.
#
# django-parltrack-votes-data is distributed in the hope that it will
# be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU General Affero Public
# License along with django-parltrack-votes.
# If not, see <http://www.gnu.org/licenses/>.
#
# Copyright (C) 2013 Laurent Peuch <cortex@worlddomination.be>
# Copyright (c) 2015 Arnaud Fabre <af@laquadrature.net>

import os
import ijson
import urllib
from os.path import join

from django.core.management.base import BaseCommand
from import_parltrack_votes.utils import parse_vote_data

# DateTime tools
from django.utils.timezone import make_aware as date_make_aware
from dateutil.parser import parse as date_parse
from pytz import timezone as date_timezone

# Models
from django.db import connection
from django.db.utils import OperationalError
from representatives_votes.models import Dossier

def _parse_date(date_str):
    return date_make_aware(date_parse(date_str), date_timezone('Europe/Brussels'))

JSON_URL = 'http://parltrack.euwiki.org/dumps/ep_votes.json.xz'
DESTINATION = join('/tmp', 'ep_votes.json')

def truncate_model(model):
    cursor = connection.cursor()
    try:
        cursor.execute('TRUNCATE TABLE "{0}"'.format(model._meta.db_table))
    except OperationalError:
        cursor.execute('DELETE FROM "{0}"'.format(model._meta.db_table)) 


class Command(BaseCommand):
    def handle(self, *args, **options):
        json_file = retrieve_xz_json(JSON_URL, DESTINATION)

        print "read file", json_file
        print "import proposals"
        truncate_model(Dossier)
        for vote_data in ijson.items(open(json_file), 'item'):
            parse_vote_data(vote_data, False)


def retrieve_xz_json(url, destination):
    "Download and extract json file from parltrack"

    if os.system("which unxz > /dev/null") != 0:
        raise Exception("XZ binary missing, please install xz")
    
    if os.path.exists(destination + '.hash'):
        with open(destination + '.hash', 'r') as f:
            etag = f.read()
    else:
        etag = False
    
    print "download lastest data dump of votes from parltrack"
    request = urllib.urlopen(url)
    request_etag = request.info()['ETag']
    
    if not etag or not etag == request_etag:
        
        if os.path.exists(destination + '.xz'):
            print "Clean old downloaded files"
            os.remove(destination + '.xz')

        if os.path.exists(destination):
            os.remove(destination)

        print "Download vote data from parltrack"
        urllib.urlretrieve(url, destination + '.xz')

        with open(destination + '.hash', 'w+') as f:
            f.write(request_etag)
            
        print "unxz it"
        os.system("unxz %s" % destination + '.xz')
    return destination

