# -*- coding: utf-8 -*-
import datetime
import re
from scrapy import Selector
from django.utils.html import remove_tags
from django.utils.dateparse import parse_datetime

from parlament.resources.extractors import BaseExtractor
from parlament.resources.extractors import SingleExtractor
from parlament.resources.extractors import MultiExtractor
from parlament.resources.util import _clean
from parlament.settings import BASE_HOST

import logging
logger = logging.getLogger(__name__)

class ST():
    regexStripTags = re.compile('<.*?>')
    @classmethod
    def strip_tags(cls, txt):
        try:
            return ''.join(cls.regexStripTags.split(txt))
        except TypeError:
            print("Cannot strip tags from {}".format(txt))
            return ''

def merge_split_paragraphs(textparts):
    """
    Re-merge paragraphs that have been divided by pagebreaks, footer lines etc.
    """
    merged = []
    for p in textparts:
        if len(p) and p[0].islower():
            pindx = len(merged) - 1
            if len(merged[pindx]) and merged[pindx][-1] == '-':
                merged[pindx] = merged[pindx][0:-1]
            merged[pindx] += p
        else:
            merged.append(p)

    return [' '.join(p.splitlines()) for p in merged]

regexTimestamp = re.compile('([0-9]{1,2} [A-Za-z]{3} [0-9]{4})')
regexFindPage = re.compile('Seite_([0-9]*)\.html')
regexSpeakerId = re.compile('WWER/(PAD_[0-9]*)/')
regexDebateNr = re.compile('/NRSITZ_([0-9]*)/')
regexLink0 = re.compile('.*?\s?\[\[link0\]\](?: \(.*?\))?:\s?', re.U | re.S)
regexAnnotation = re.compile('\[\[(?:link|com)\d+\]\]', re.U | re.S)
SPEAKER_CLASSES = ['Abgeordneter', 'Abgeordnete']
PRES_CLASSES = ['Präsident', 'Präsidentin']
PARAGRAPH_CLASSES = ['MsoNormal', 'StandardRB', 'StandardRE', 'MsoListBullet']

"""
    elemente mit xpath finden - danach mit index/footnote ersetzen (regex)
    auf html ? danach wieder saubere tags einfügen ?
"""

class RSS_DEBATES(MultiExtractor):

    """
    Debate meta data (inlcuding the url to the detailed transcript) from
    RSS feed.
    """
    XPATH = '//item'

    class RSSITEM(SingleExtractor):

        """
        An rss-item of the feed, representing a single debate.
        """
        class TITLE(SingleExtractor):
            XPATH = './/title/text()'

        class DETAIL_LINK(SingleExtractor):
            XPATH = './/link/text()'

        class DATE(SingleExtractor):
            XPATH = './/pubDate/text()'

        class DESCRIPTION(SingleExtractor):
            XPATH = './/description/text()'

        class PROTOCOL_URL(SingleExtractor):
            XPATH = './/a[contains(@href, \'html\')]/@href'

        @classmethod
        def xt(cls, response):

            # Debatedate
            dtime = None
            try:
                dtime = datetime.datetime.strptime(
                    regexTimestamp.findall(cls.DATE.xt(response))[0],
                    '%d %b %Y')
            except (IndexError, ValueError):
                logger.warn(u"Could not parse date '{}'".format(dtime_text))

            # Protocol URL from description field
            descr = Selector(text=cls.DESCRIPTION.xt(response))
            protocol_url = cls.PROTOCOL_URL.xt(descr)

            # Debate-nr from protocol url
            dnr = None
            try:
                dnr = int(regexDebateNr.findall(protocol_url)[0])
            except (IndexError, ValueError):
                logger.warn(u"Could not parse debate_nr from '{}'".format(protocol_url))

            return {
                'date': dtime,
                'debate_type': None, #  is part of the url, actually
                'title': cls.TITLE.xt(response),
                'protocol_url': protocol_url,
                'nr': dnr,
                'detail_url': cls.DETAIL_LINK.xt(response)
            }

    @classmethod
    def xt(cls, response):
        return [cls.RSSITEM.xt(item) for item in response.xpath(cls.XPATH)]


class DOCSECTIONS(MultiExtractor):

    """
    Parts of a debate document
    These sections are helpful to construct the statements.
    """
    XPATH = '//div[contains(@class, \'Section\')]'
    pclasses = set()  # to keep track of P's classes we find

    class CLASSINFO(MultiExtractor):
        XPATH = '@class'

    class TIMESTAMPS(MultiExtractor):
        """
        Paragraphs by classname that indicates timestamp-content
        """
        XPATH = './/p[re:test(@class, "^(RB|RE)")]'

    class HREF(SingleExtractor):
        XPATH = '@href'

    class NAME(SingleExtractor):
        XPATH = '@name'

    class TEXT(SingleExtractor):
        XPATH = 'text()'

    class CONTENT_PLAIN(SingleExtractor):
        """
        TODO: sometimes , RE classes contain actual text
        """
        @classmethod
        def _is_text(cls, response):
            pclass = None
            try:
                pclass = response.xpath('.//@class').extract().pop().strip()
            except:
                pass
            if pclass in PARAGRAPH_CLASSES or pclass is None:
                return True

        @classmethod
        def xt(cls, response):
            """
            Paragraphs by classname that indicates content of a statement.
            """
            return [t for t in response.xpath('p') if cls._is_text(t)]

    class CONTENT(SingleExtractor):
        """
        Main, textual content of the section
        """
        @classmethod
        def xt(cls, response):
            textparts = []
            for txt in response.xpath('p'):
                textparts.append(txt.extract())
            return '\n\n'.join([' '.join(p.splitlines()) for p in textparts])

    @classmethod
    def _clean_timestamps(cls, timestamps):
        """
        Parse potential timestamp-strings to numeric (min, sec) tuples
        """
        ts = []
        for t in filter(lambda v: len(v) >= 2, timestamps):
            try:
                ts.append([int(v) for v in t.split('.')])
            except ValueError:
                logger.warn(u"Value error in timestamp: '{}'".format(t))
        return ts


    @classmethod
    def xt(cls, response):
        """
        Extract sections (statements) from document (protocol)

        A section is a div-element `<div class="WordSection..">` that
        contains a single speech in paragraphs of text.
        It also contains entity-links, i-elements (for explanatory
        comments not part of the actual speech), as well as page-numbers,
        time-stamps and other artefacts.

        """
        sections = []
        current_maxpage = None
        current_timestamp = None

        for item_index, item in enumerate(response.xpath(cls.XPATH)):
            pages = []
            links = []
            annotated = ""
            plaintext = ""

            # Parse section
            rawtext = cls.CONTENT.xt(item)
            classnames = cls.CLASSINFO.xt(item)
            timestamps = [ST.strip_tags(ts)
                          for ts in cls.TIMESTAMPS.xt(item)]

            # P-looping, carry out annotations
            # TODO: fails when there are links inside of comments, when this
            #   happens, matched tag from the original text does not match
            #   the already changed/replaced tag in the working-buffer
            # EDIT: replacing I/comments first - that means we might have
            #   a link inside a comment - have to deal with that, too (e.g. by
            #   specifically looking for markup in the replaced comments)
            paragraphs = []
            for p in cls.CONTENT_PLAIN.xt(item):
                html = p.extract()
                replacelinks = [a.extract() for a in p.xpath('.//a[@href]')]
                for i, com in enumerate(p.xpath('.//i')):
                    if ST.strip_tags(com.extract()).startswith('('):
                        html = html.replace(com.extract(), '[[com{}]]'.format(i))
                for i, a in enumerate(replacelinks):
                    html = html.replace(a, '[[link{}]]'.format(i))

                plain = ST.strip_tags(html).strip()
                if plain != '':
                    paragraphs.append(plain)

            annotated = "\n\n".join(paragraphs)

            # Loop over P's again + remove annotations entirely
            plain_paragraphs = []
            for plain in paragraphs:
                # Replace speaker part, if any
                try:
                    match = regexLink0.findall(plain)[0]
                    plain = plain.replace(match, '')
                except IndexError:
                    pass

                # Replace all coms+links
                for match in regexAnnotation.findall(plain):
                    plain = plain .replace(match, '')

                plain_paragraphs.append(plain)

            # Attempt to re-merge some paragraphs
            plain_paragraphs = merge_split_paragraphs(plain_paragraphs)

            # Collect links
            for a in item.xpath('.//a[@href]'):
                links.append((cls.HREF.xt(a), cls.TEXT.xt(a)))

            # Look for page-number
            for a in item.xpath('.//a[@name]'):
                name = cls.NAME.xt(a)
                nms = regexFindPage.findall(name)
                if len(nms):
                    pages.append(int(nms[0]))

            # If we have page(s) or timestamp(s) in this section,
            # keep them for possible later reference
            if len(pages):
                current_maxpage = max(pages)
            timestamps = cls._clean_timestamps(timestamps)
            if len(timestamps):
                current_timestamp = max(timestamps)

            res = {'raw_text': rawtext,
                   'full_text': "\n\n".join(plain_paragraphs),
                   'annotated_text': annotated,
                   'doc_section': classnames[0] if len(classnames) else None,
                   'links': links,
                   'timestamps': timestamps,
                   'ref_timestamp': current_timestamp,
                   'time_start': min(timestamps) if len(timestamps) else None,
                   'time_end': max(timestamps) if len(timestamps) else None,
                   'page_start': min(pages) if len(pages) else current_maxpage,
                   'page_end': max(pages) if len(pages) else current_maxpage,
                   }

            res['text_type'] = StatementPostprocess.detect_sectiontype(res)
            res['speaker_name'] = StatementPostprocess.get_speaker_name(res)
            res['speaker_id'] = StatementPostprocess.get_speaker_id(res)
            res['speaker_role'] = StatementPostprocess.get_speaker_role(res)

            # StatementPostprocess.get_parts(response)

            sections.append(res)
        return sections


class StatementPostprocess():

    """
    Extract speaker name, party, title and role
    """

    TAG_SPKR_ROLE_PRES = 'pres'
    TAG_SPKR_ROLE_OTHER = 'other'

    TAG_STMT_REGULAR = 'reg'
    TAG_STMT_OTHER = 'other'

    @classmethod
    def detect_sectiontype(cls, data):
        """ Detect the type of section from the data we extracted
        so far.
            - look at the first link, and test if it links to
              a person profile
            (- alternatively, we could test if the first line
               matches the  regular expression "<title> <name>:" )
        """
        stype = cls.TAG_STMT_OTHER
        if len(data['links']):
            href = data['links'][0][0]
            if 'WWER' in href:
                stype = cls.TAG_STMT_REGULAR
        return stype

    @classmethod
    def get_speaker_name(cls, data):
        """ Get from the first of the extracted links """
        if len(data['links']):
            return data['links'][0][1]

    @classmethod
    def get_speaker_id(cls, data):
        """ Get from the first of the extracted links """
        if len(data['links']):
            ids = regexSpeakerId.findall(data['links'][0][0])
            if ids:
                return ids[0]

    @classmethod
    def get_speaker_role(cls, data):
        """ By examining the first word of the section """
        return cls.TAG_SPKR_ROLE_PRES \
               if data['full_text'].startswith(u'Präs') \
               else cls.TAG_SPKR_ROLE_OTHER


"""
# Parse content of statement
for el in scrapy.Selector(text=statement.raw_text).xpath('.//p/text()'):
    print el.extract().encode('utf8')
for el in scrapy.Selector(text=statement.raw_text).xpath('.//*'):
    # all elements
    print el.extract().encode('utf8')


# Create xml
import xml
el = xml.dom.minidom.Element('p')
textel = xml.dom.minidom.Text()
textel.dat = 'hi'
el.appendChild(textel)
el.toxml()


loop over P's
    - loop over

"""
