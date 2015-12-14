# -*- coding: utf-8 -*-
"""
Create an export from the scraped data.
(E.g. for using the data in external projects )
"""

from __future__ import absolute_import
from django.core.management.base import BaseCommand
from op_scraper import models
import json
import io

class Command(BaseCommand):

    def run_from_argv(self, argv):
        self._argv = argv
        self.execute()

    def handle(self, *args, **options):
        llpnr = None
        try:
            llpnr = int(self._argv[2])
        except (IndexError, ValueError):
            pass

        if llpnr:
            llps = models.LegislativePeriod.objects.filter(number=llpnr)
        else:
            llps = models.LegislativePeriod.objects.all()
        for llp in llps:
            for debate in models.Debate.objects.filter(llp=llp):
                statements = []
                for stmt in debate.debate_statements.all():
                    statements.append(self._map(stmt))
                fname = 'export-{}-{}.json'.format(llp.number, debate.nr)
                if len(statements):
                    with io.open('export/' + fname, 'w+', encoding='utf8') as f:
                        data = json.dumps(statements, indent=2, ensure_ascii=False)
                        f.write(data)
                    print("Wrote {}".format(fname))

    def _map(self, stmt):
        """
        De-normalize and add data about person and llp to statement
        """
        items = [('text', stmt.full_text),
                 ('date', unicode(stmt.date)),
                 ('len', len(stmt.full_text))]

        if stmt.person is not None:
            items+=[
                ('name', stmt.person.full_name),
                ('birthdate', unicode(stmt.person.birthdate)),
                ('current_party', unicode(stmt.person.party)),
                # ('deceased': False)
            ]
            if stmt.date is not None and stmt.person.birthdate is not None:
                try:
                    dt = stmt.date - stmt.person.birthdate
                    items+=[('age', int(dt.days / 365.25))]
                except:
                    pass

        if stmt.debate is not None:
            items+=[('session_nr', stmt.debate.nr)]
            if stmt.debate.llp is not None:
                items+=[('llp', stmt.debate.llp.number)]

        return dict(items)


