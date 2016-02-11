from django import test

import mock

from representatives_votes.models import Dossier
from representatives_votes.signals import sync


class SyncTest(test.TestCase):
    MODELS = 'representatives_votes.contrib.parltrack.models'

    def test_sync_dossier_receiver(self):
        parltrack = Dossier.objects.create(
            reference='parltrack',
            title='from parltrack',
            link='http://www.europarl.europa.eu/foo'
        )

        other = Dossier.objects.create(
            reference='other',
            title='from other',
            link='http://other/foo'
        )

        with mock.patch('%s.sync_dossier' % self.MODELS) as sync_dossiers:
            sync.send(sender=Dossier, instance=parltrack)
            sync.send(sender=Dossier, instance=other)

        assert sync_dossiers.call_args_list == [mock.call('parltrack')]
