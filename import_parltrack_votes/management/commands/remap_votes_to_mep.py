# coding: utf-8

from django.core.management.base import BaseCommand

from import_parltrack_votes.models import Matching
from representatives_votes.models import Vote

class Command(BaseCommand):
    """
    Redo the mapping between votes and representatives based on 
    matching table
    """

    def handle(self, *args, **options):
        """ TODO : test between :
         - for all matching entry find matching vote
         - for all vote find matching entry
        """
        matchings = Matching.objects.exclude(representative_remote_id=None)
        for matching in matchings:
            mep_name = '%s (%s)' % (matching.mep_name, matching.mep_group)
            votes = Vote.objects.filter(
                representative_name=mep_name,
                representative_remote_id=None
            )
            for vote in votes:
                print(vote)
