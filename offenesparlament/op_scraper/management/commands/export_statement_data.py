from django.core.management.base import BaseCommand
from op_scraper.models import DebateStatement, Person
import csv
from os import system, path


class Command(BaseCommand):
    EXPORT_DEST = 'export'
    help = 'Exports Statement Data'

    def add_arguments(self, parser):
        parser.add_argument('--llp', type=int)
        parser.add_argument('--export', action='store_true')

    def handle(self, *args, **options):

        if options['llp'] is not None:
            statements = DebateStatement.objects.filter(debate__llp__number=options['llp'])
        else:
            statements = DebateStatement.objects.all()


        export_preview = statements[0:25]
        for statement in export_preview:
            # print(statement.full_text)
            print(
                statement.date,
                statement.speaker_name,
                statement.person,
                statement.debate.llp.number
            )

        if options['export']:
            for statement in statements:
                exportfile = path.join(self.EXPORT_DEST, str(statement.pk) + '.txt')
                with open(exportfile, 'w') as dest:
                    dest.write(statement.full_text.encode('utf-8'))
