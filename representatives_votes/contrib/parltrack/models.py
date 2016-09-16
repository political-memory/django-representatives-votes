from representatives_votes.models import Dossier
from representatives_votes.signals import sync

from import_dossiers import sync_dossier


def sync_dossier_receiver(sender, instance, **kwargs):
    if not instance.link.startswith('http://www.europarl.europa.eu'):
        return

    sync_dossier(instance.reference)
sync.connect(sync_dossier_receiver, sender=Dossier)
