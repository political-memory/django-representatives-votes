# coding: utf-8

import os


class TestDataSource:
    base = os.path.join(os.path.dirname(__file__), 'data', 'parltrack')

    def dossier(self, reference):
        path = '%s_dossier_%s.json' % (self.base, reference.replace('/', '-'))
        return open(path, 'r')
