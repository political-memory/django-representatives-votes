from django import test


class RetrieverSpec(test.TestCase):
    # Should:
    # - sync any dossier where title='', dossiers are inserted by a custom
    # admin feature
    # - sync any proposal without vote, proposals should be added on
    # dossier-sync, so any dossier in our db should have votes for every
    # proposal at some point.

