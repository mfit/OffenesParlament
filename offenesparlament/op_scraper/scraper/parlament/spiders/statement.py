# -*- coding: utf-8 -*-
import scrapy
import feedparser
import roman
from urllib import urlencode

from ansicolor import green, red, yellow

from parlament.settings import BASE_HOST
from parlament.spiders import BaseSpider
from parlament.resources.extractors.statement import (
    RSS_DEBATES,
    RSS_DEBATES_SIMPLE,
    HTML_DEBATE_DETAIL,
    DOCSECTIONS
)

from op_scraper.models import DebateStatement, Debate
from op_scraper.models import Person, LegislativePeriod

import datetime

import json


def debatelist_makeurl_rss(llp, debatetype):
    baseurl = "{}/{}".format(BASE_HOST, "PAKT/STPROT/filter.psp")
    params = {
        'view': 'RSS',
        'NRBRBV': debatetype,
        'GP': llp,
        'R_PLSO': 'PL',
        'NUR_VORL': 'N',
        'FBEZ': 'FP_011',
        'listeId': '212',
    }
    return baseurl + '?' + urlencode(params)


class StatementSpider(BaseSpider):

    """
    Spider to scrape debates and debate statements
    ----------------------------------------------

    Start the spider by specifying `llp` and `type` parameters.

    First step is to get urls of debate-transcripts ("stenographische
    protokolle"), for this, the RSS-Feed at
    `http://www.parlament.gv.at/PAKT/STPROT/` is used.
    We have to do one extra step to get the actual protocol url from an
    intermediate debate-detail page.

    Parameters are `type` (NR, BR) and `llp` (number) for type of
    debate and llp respectively::

        ./manage.py scrape crawl statement -a llp=24 -a type=NR

    To limit the debate list, use `snr` to scrape only debates that
    have 'snr' in the title::

        ./manage.py scrape crawl statement -a llp=24 -a type=NR\
        -a snr=171

    """


    BASE_URL = "{}/{}".format(BASE_HOST, "PAKT/STPROT")
    ALLOWED_LLPS = range(20, 26)
    DEBATETYPES = ['NR', 'BR']

    name = "statement"

    def __init__(self, **kw):
        super(StatementSpider, self).__init__(**kw)

        if 'type' in kw and kw['type'] in self.DEBATETYPES:
            self.DEBATETYPES = [kw['type']]
        if 'llp' in kw and kw['llp'] != 'all':
            try:
                self.LLP = [roman.toRoman(int(kw['llp']))]
            except:
                self.LLP = [kw['llp']]
        else:
            self.LLP = [roman.toRoman(llp) for llp in self.ALLOWED_LLPS]

        # Sitzungsnummer (further filtering down to just one 'sitzung')
        self.SNR = kw['snr'] if 'snr' in kw else None

        # The start url is actually not parsed at all, but we need some
        # url to get the scraping started.
        self.start_urls = [self.BASE_URL]

    def parse(self, response):
        """
        Starting point - produces urls (requests) of debate items lists (urls
        of RSS feeds).

        It builds the list of requests/callbacks (alongsite metadata that
        is known beforenhand) from the set of LLPs and debate types.

        The feeds will be parsed in the next step, parse_debatelist.
        """

        callback_requests = []
        for llp in self.LLP:
            for nrbr in self.DEBATETYPES:
                # Debatelist Url
                feed_url = debatelist_makeurl_rss(llp, nrbr)

                # Additional metadata (does a lookup on the LLP)
                llp_item = None
                try:
                    llp_item = LegislativePeriod.objects.get(roman_numeral=llp)
                except LegislativePeriod.DoesNotExist:
                    self.logger.warning(red(u"LLP '{}' not found".format(llp)))

                # Add a request and callback
                callback_requests.append(
                    scrapy.Request(feed_url,
                                   callback=self.parse_debatelist,
                                   meta={'llp': llp_item, 'type': nrbr}))

        return callback_requests

    def parse_debatelist(self, response):
        """
        Parse feed of debate items.

        Each response is an RSS feed with debate items.
        From each item (=debate), debate metadata and a detail url (not yet
        the debate protocol url) is extracted.

        The detail url is parsed in the next step, parse_debate_detail.
        """

        llp = response.meta['llp'] if 'llp' in response.meta else None
        debate_type = response.meta['type'] if 'type' in response.meta else ''

        # debates = RSS_DEBATES.xt(response)
        debates = RSS_DEBATES_SIMPLE.xt(response)

        # If SNR is set filter debate list to contain the debate number.
        fetch_debates = filter(lambda r: r['detail_url'] != "" and
                               (not self.SNR or self.SNR in r['title']),
                               debates)

        self.logger.info(green(u"{} of {} debates from {}".format(
            len(fetch_debates), len(debates), response.url)))

        for debate in fetch_debates:
            debate['llp'] = llp
            debate['debate_type'] = debate_type
            yield scrapy.Request(debate['detail_url'],
                                 callback=self.parse_debate_detail,
                                 meta={'debate': debate})


    def parse_debate_detail(self, response):
        """
        Process a detail page that contains the url to the debate protocol.

        Extract the protocol url, add it to metadata to return the request
        with the callback for the actual content parsing of the debate.

        The debate metadata is saved, and the next step is to parse the
        actual debate content, parse_debate
        """

        # Complete debate metadata and store (insert/update) it
        debate = response.meta['debate']
        debate['protocol_url'] = BASE_HOST + HTML_DEBATE_DETAIL.xt(response)
        debate_item = self.store_debate(debate)

        yield scrapy.Request(
            debate['protocol_url'],
            callback=self.parse_debate,
            meta={'debate': debate_item})

    def parse_debate(self, response):
        """
        Debate-transcript ("Stenografisches Protokoll") parser.

        Parses the actual debate content.
        """
        i = 0
        for i, sect in enumerate(DOCSECTIONS.xt(response)):
            # Lookup + add references to the section data
            sect['debate'] = response.meta['debate']
            if 'speaker_id' in sect and sect['speaker_id'] is not None:
                try:
                    sect['person'] = Person.objects.get(
                        parl_id=sect['speaker_id'])
                except Person.DoesNotExist:
                    self.logger.warning(
                        red(u"Person '{}' not found".format(sect['speaker_id'])))
            else:
                sect['person'] = None

            # Select best timestamps for start and end and make datetime
            start_ts = sect['time_start'] or sect['ref_timestamp']
            end_ts = sect['time_end'] or sect['ref_timestamp']
            try:
                debate_date = sect['debate'].date()
            except:
                # Use some valid date, but recognizable to come from a parse error
                debate_date = datetime.datetime(2057, 1, 1)
            sect['date'] = self._apply_ts(debate_date, start_ts)
            sect['date_end'] = self._apply_ts(debate_date, end_ts)

            self.store_statement(sect, i)

        self.logger.info(
            green(u"Saved {} sections from {}".format(i, response.url)))

    def store_debate(self, data):
        """
        Save (update or insert) debate to ORM
        """
        try:
            debate = Debate.objects.get(llp=data['llp'], nr=data['nr'])
        except Debate.DoesNotExist:
            debate = Debate()
        for (key, value) in data.items():
            setattr(debate, key, value)
        debate.save()
        self.logger.info(green(u"Debate metadata saved {}".format(debate)))
        return debate

    def store_statement(self, data, index=-1):
        """
        Save (update or insert) debate_statement to ORM
        """
        data['index'] = int(index)
        self.logger.info(data)
        try:
            debate_statement = DebateStatement.objects.get(
                debate=data['debate'], doc_section=data['doc_section'])
        except DebateStatement.DoesNotExist:
            debate_statement = DebateStatement()
        keys = set(data.keys()) &\
            set([v.name for v in DebateStatement._meta.get_fields()])
        for key in keys:
            setattr(debate_statement, key, data[key])
        debate_statement.save()

    def _apply_ts(self, date, timeparts):
        """
        Apply hour, minutes and possibly secconds to a date.

        In the docsections, we scrape only minutes and seconds - but we
        have the date from the debate metadata.
        This helper method combines the two to get a full timestamp.
        """
        if timeparts is not None and len(timeparts) >= 2:
            ts = {'hour': timeparts[0],
                  'minute': timeparts[1],
                  'second': timeparts[2]
                  if len(timeparts) > 2 else 0}
            date = date.replace(**ts)
        return date
