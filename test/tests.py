import copy
import os

from django.core.management import call_command
from django.core.serializers.json import Deserializer
from django.test import TestCase

from representatives.contrib import parltrack
from representatives.models import Representative
from representatives_votes.contrib.parltrack import import_dossiers
from representatives_votes.contrib.parltrack import import_single_dossier
from representatives_votes.contrib.parltrack import import_votes
from representatives_votes.models import Dossier, Proposal, Vote


class ImportTest(TestCase):
    def setUp(self):
        for model in (Representative, Dossier, Proposal, Vote):
            model.objects.all().delete()

    def _get_datapath(self, file):
        return os.path.join(os.path.dirname(__file__), 'data', file)

    def _test_import(self, scenario, callback):
        fixture = self._get_datapath('%s_fixture.json' % scenario)
        expected = self._get_datapath('%s_expected.json' % scenario)

        # Disable django auto fields
        exclude = ('id', '_state', 'created', 'updated')

        with open(fixture, 'r') as f:
            callback(f)

        with open(expected, 'r') as f:
            for obj in Deserializer(f.read()):
                compare = copy.copy(obj.object.__dict__)

                for f in exclude:
                    if f in compare:
                        compare.pop(f)

                type(obj.object).objects.get(**compare)

    def test_parltrack_import_dossiers(self):
        with self.assertNumQueries(15):
            self._test_import('dossiers', import_dossiers.main)

    def test_parltrack_import_single_dossier(self):
        call_command('loaddata', os.path.join(os.path.abspath(
            parltrack.__path__[0]), 'tests', 'representatives_expected.json'))

        with self.assertNumQueries(16):
            self._test_import('single', import_single_dossier.main)

    def test_parltrack_import_votes(self):
        call_command('loaddata', os.path.join(os.path.abspath(
            parltrack.__path__[0]), 'tests', 'representatives_expected.json'))
        call_command('loaddata', self._get_datapath('dossiers_expected.json'))

        with self.assertNumQueries(65):
            self._test_import('votes', import_votes.main)

    def test_dossier_sync(self):
        call_command('loaddata', self._get_datapath('sync_initial.json'))

        dossier = Dossier.objects.get(reference='2012/2002(INI)')

        with self.assertNumQueries(3):
            dossier.sync()

        exp = "Agenda for change: the future of EU development policy"
        assert dossier.title == exp

    def test_dossier_sync_norefresh(self):
        call_command('loaddata', self._get_datapath('sync_initial.json'))

        dossier = Dossier.objects.get(reference='2012/2002(INI)')

        with self.assertNumQueries(2):
            dossier.sync(False)

        assert dossier.title == 'initial title'

        dossier.refresh_from_db()

        exp = "Agenda for change: the future of EU development policy"
        assert dossier.title == exp
