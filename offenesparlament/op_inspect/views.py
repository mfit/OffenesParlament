# -*- coding: UTF-8 -*-
from django.shortcuts import render, redirect
import op_scraper.models as models
from django.db.models import Count, Max
import datetime
from django.utils.safestring import mark_safe
from scrapy import Selector
from op_scraper.scraper.parlament.resources.extractors import statement

def index(request, value=None):
    llps = models.LegislativePeriod.objects.all()
    debates = []
    debate = False
    statements = []
    llp = None
    stats = {'text':{}, 'speaker':{}}
    if 'llpnr' in request.GET:
        llp = models.LegislativePeriod.objects.get(
            number=int(request.GET['llpnr']))
        debates = models.Debate.objects.filter(llp=llp)

    if llp and 'debate_nr' in request.GET and request.GET['debate_nr']:
        debate = models.Debate.objects.get(
          llp=llp,
          nr=int(request.GET['debate_nr']))
        for s in  debate.debate_statements.order_by('index').all():
            # links = Selector(text=s.raw_text).xpath('.//a')
            statements.append({
                #"links": links,
                "model": s,
                "orig": mark_safe(s.raw_text),
                "annotated": mark_safe(s.annotated_text),
                "clean": s.full_text,
            })

            stats['speaker'][s.speaker_role] = stats['speaker'].setdefault(s.speaker_role, 0) + 1
            stats['text'][s.text_type] = stats['text'].setdefault(s.text_type, 0) + 1

    return render(request, 'inspect.html',
                  context={'llps':llps,
                           'show_orig': ('show_orig' in request.GET\
                                         and request.GET['show_orig']),
                           'llpnr': llp.number if llp else False,
                           'debates': sorted(debates, key=lambda d: d.nr),
                           'debate': debate,
                           'stats': stats,
                           'statements': statements})


