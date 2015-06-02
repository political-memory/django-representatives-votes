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
        # votes = SELECT * FROM votes WHERE representative_name = CONCAT(matching.mep_name, ' (', matching.mep_group, ')') AND matching_remote_id = None AND representative_remote_id = None
        '''
        votes = Vote.objects.raw('
        SELECT * FROM
        "representatives_votes_vote" as vote
        LEFT JOIN "import_parltrack_votes_matching" as matching
        ON vote.representative_name = CONCAT(matching.mep_name, " (", matching.mep_group, ")")
        WHERE matching.representative_remote_id IS NULL AND
        vote.representative_remote_id IS NOT NULL')
        '''
        # print(votes.query)
