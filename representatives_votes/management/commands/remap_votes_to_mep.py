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
# Copyright (c) 2015 Arnaud Fabre <af@laquadrature.net>
from __future__ import absolute_import

import re

from django.core.management.base import BaseCommand

from representatives_votes.models import Vote

from import_parltrack_votes.utils import find_matching_representatives_in_db

class Command(BaseCommand):
    """
    Redo the mapping between votes and representatives based on 
    matching table
    """

    def handle(self, *args, **options):
        votes = Vote.objects.filter(
            representative=None
        )
        for vote in votes:
            m = re.search(
                r'^([\w ]+) \((\w+)\)$',
                vote.representative_name,
                flags=re.UNICODE
            )
            name, group = m.group(1), m.group(2)
            r = find_matching_representatives_in_db(
                name,
                vote.proposal.datetime,
                group
            )
            if r:
                vote.representative = r
                vote.save()
