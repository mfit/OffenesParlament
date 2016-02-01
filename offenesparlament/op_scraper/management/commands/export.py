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
import datetime

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
            fname = 'export-{}.json'.format(llp.number)
            with io.open('export/' + fname, 'w+', encoding='utf8') as f:
                for debate in models.Debate.objects.filter(llp=llp):
                    for stmt in debate.debate_statements.all():
                        f.write(u"\n")
                        f.write(u'{"index":{}}\n')
                        f.write(json.dumps(self._map(stmt),
                                           ensure_ascii=False) + u"\n")
            print("Wrote {}".format(fname))

    def _map(self, stmt):
        """
        De-normalize and add data about person and llp to statement
        """

        items = [('text', stmt.full_text),
                 ('date', self._convdate(stmt.date)),
                 ('duration', self._convduration(stmt.date, stmt.date_end)),
                 ('wordlen', len(stmt.full_text.split())),
                 ('role', stmt.speaker_role)]

        if stmt.person is not None:
            items+=[
                ('name', stmt.person.full_name),
                ('birthdate', self._convdate(stmt.person.birthdate)),
                ('deathdate', self._convdate(stmt.person.deathdate)),
                ('deceased', bool(stmt.person.deathdate)),
                ('current_party', unicode(stmt.person.party)),
                ('occupation', unicode(stmt.person.occupation.strip())),
                ('image', unicode(stmt.person.photo_link)),
            ]

            # if stmt.date is not None and stmt.person.birthdate is not None:
            #     try:
            #         dt = stmt.date - datetime.datetime.combine(
            #                             stmt.person.birthdate,
            #                             datetime.datetime.min.time())
            #         items+=[('age', int(dt.days / 365.25))]
            #     except TypeError:
            #         pass

        if stmt.debate is not None:
            items+=[('session_nr', stmt.debate.nr)]
            if stmt.debate.llp is not None:
                items+=[('llp', stmt.debate.llp.number)]

        return dict(items)

    def _convdate(self, val):
        return val.isoformat() if val is not None else None

    def _convduration(self, begin, end):
        duration = 0
        try:
            duration = end - begin
        except TypeError:
            pass  # stmt.date and/or stmt.date_end are None

        return duration.seconds if type(duration) == datetime.timedelta else 0

