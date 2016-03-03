# -*- coding: UTF-8 -*-
from django.shortcuts import render, redirect
from op_scraper.models import Person
from op_scraper.models import Law
from op_scraper.models import LegislativePeriod
from op_scraper.models import Keyword
from op_scraper.models import Debate, DebateStatement
from django.db.models import Count, Max

import datetime


def index(request):
    return render(request, 'index.html')


def about(request):
    return render(request, 'about.html')


def subscriptions(request):
    return render(request, 'subscriptions.html')


def person_list(request):
    llp = _ensure_ggp_is_set(request)
    return redirect('person_list_with_ggp', ggp=llp.roman_numeral)


def keyword_list(request):
    llp = _ensure_ggp_is_set(request)
    return redirect('keyword_list_with_ggp', ggp=llp.roman_numeral)


def gesetze_list(request):
    llp = _ensure_ggp_is_set(request)
    return redirect('laws_list_with_ggp', ggp=llp.roman_numeral)


def person_list_with_ggp(request, ggp):
    llp = _ensure_ggp_is_set(request, ggp)
    person_list = Person.objects \
        .filter(mandates__legislative_period=llp) \
        .order_by('reversed_name') \
        .select_related('latest_mandate__party')
    context = {'person_list': person_list}
    return render(request, 'person_list.html', context)


def gesetze_list_with_ggp(request, ggp):
    llp = _ensure_ggp_is_set(request, ggp)
    laws = Law.objects \
        .filter(legislative_period=llp) \
        .annotate(last_update=Max('steps__date')) \
        .order_by('-last_update') \
        .select_related('category')
    context = {'laws': laws}
    return render(request, 'gesetze_list.html', context)


def keyword_list_with_ggp(request, ggp):
    llp = _ensure_ggp_is_set(request, ggp)
    today = datetime.date.today()
    eight_weeks_ago = today - datetime.timedelta(weeks=8)
    top10_keywords = Keyword.objects \
        .filter(laws__steps__date__gte=eight_weeks_ago) \
        .annotate(num_steps=Count('laws__steps')) \
        .annotate(last_update=Max('laws__steps__date')) \
        .order_by('-num_steps')[:10]
    keywords = Keyword.objects.filter(laws__legislative_period=llp) \
        .order_by('title') \
        .distinct()
    context = {'top10_keywords': top10_keywords, 'keywords': keywords}
    return render(request, 'keyword_list.html', context)


def person_detail(request, parl_id, name):
    person = Person.objects.get(parl_id=parl_id)
    keywords = Keyword.objects \
        .filter(laws__steps__statements__person=person) \
        .annotate(num_steps=Count('laws__steps')) \
        .order_by('-num_steps')[:10]
    laws = Law.objects \
        .filter(steps__statements__person=person) \
        .annotate(last_update=Max('steps__date')) \
        .order_by('-last_update')
    context = {'person': person, 'keywords': keywords, 'laws': laws}
    return render(request, 'person_detail.html', context)


def gesetz_detail(request, parl_id, ggp=None):
    parl_id_restored = '({})'.format(
        parl_id.replace('-', '/').replace('_', ' '))
    if ggp:
        llp = LegislativePeriod.objects.get(roman_numeral=ggp)
        gesetz = Law.objects.get(
            parl_id=parl_id_restored, legislative_period=llp)
    else:
        llp = None
        gesetz = Law.objects.get(parl_id=parl_id, legislative_period=llp)
    context = {'law': gesetz}
    return render(request, 'gesetz_detail.html', context)


def keyword_detail(request, keyword):
    keyword = Keyword.objects.get(_title_urlsafe=keyword)
    laws = keyword.laws \
        .annotate(last_update=Max('steps__date')) \
        .order_by('-last_update')
    context = {'keyword': keyword, 'laws': laws}
    return render(request, 'keyword_detail.html', context)


def _ensure_ggp_is_set(request, ggp_roman_numeral=None):
    """Make sure a valid GGP is set as session var and set the current one if
    it isn't. Return the selected GGP's roman numeral."""
    if ggp_roman_numeral is not None:
        llp = LegislativePeriod.objects.get(roman_numeral=ggp_roman_numeral)
        request.session['ggp_roman_numeral'] = llp.roman_numeral
        request.session['ggp_facet_repr'] = llp.facet_repr
    elif 'ggp_roman_numeral' not in request.session or request.session['ggp_roman_numeral'] is None:
        llp = LegislativePeriod.objects.get_current()
        request.session['ggp_roman_numeral'] = llp.roman_numeral
        request.session['ggp_facet_repr'] = llp.facet_repr
    llp = LegislativePeriod.objects.get(
        roman_numeral=request.session['ggp_roman_numeral'])
    return llp

def debate_list(request):
    debates = Debate.objects.select_related('llp').order_by('date', 'nr')
    context = {'debates': debates}
    return render(request, 'debate_list.html', context)

def debate_detail(request, id):
    debate = Debate.objects.select_related('llp').get(id=id)
    def stmtprepare(stmt):
        try:
            stmt.time_anchor = '-'.join([n.strip().zfill(2) for n in
                                         stmt.time_start[1:-1].split(',')[0:2]])
        except:
            stmt.time_anchor = ''
        return stmt
    statements = map(stmtprepare,
                     debate.debate_statements.select_related('person')
                                .filter(text_type='reg')
                                .order_by('index'))
    context = {'debate': debate, 'statements': statements}
    return render(request, 'debate_detail.html', context)
