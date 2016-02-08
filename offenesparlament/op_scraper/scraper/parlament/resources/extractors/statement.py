# -*- coding: utf-8 -*-
import datetime
import re
from xml.dom import minidom
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

regexTimestamp = re.compile('([0-9]{1,2} [A-Za-z]{3} [0-9]{4})')
regexFindPage = re.compile('Seite_([0-9]*)\.html')
regexSpeakerId = re.compile('WWER/(PAD_[0-9]*)/')
regexDebateNr = re.compile('/NRSITZ_([0-9]*)/')
regexSpeakerPart = re.compile('.*?\s?\[\[link\d+\]\](?: \(.*?\))?:\s?', re.U | re.S)
regexAnnotation = re.compile('\[\[(?:link|com)\d+\]\]', re.U | re.S)

class Paragraph():
    def __init__(self, plain, links=None, comments=None):
        self.plain = plain
        self.links = links
        self.comments = comments


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
                logger.warn(
                    u"Could not parse debate_nr from '{}'".format(protocol_url))

            return {
                'date': dtime,
                'debate_type': None,  # is part of the url, actually
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
    Actual debate contents. Statements, parts of a debate document.
    These sections are helpful to construct the statements.
    For llp >= 22, every section is a speech - except for some sections at
    the beginning or end of a protocol.
    """
    XPATH = '//div[contains(@class, \'Section\')]'
    replace_id = 1  # Used to give unique ids to parts for replacement

    # Tags for speaker role
    TAG_SPKR_ROLE_PRES = 'pres'
    TAG_SPKR_ROLE_ABG = 'abg'
    TAG_SPKR_ROLE_OTHER = 'other'

    # Tags for section-type (is regular debate-speech,
    # or some other text e.g. intro on top of debate protocol)
    TAG_STMT_REGULAR = 'reg'
    TAG_STMT_OTHER = 'other'

    PARAGRAPH_CLASSES = [
        'MsoNormal',
        'StandardRB',
        'StandardRE',
        'MsoListBullet',
        # 'ZM'  # Problematic
    ]

    class CLASSINFO(MultiExtractor):
        """ Get class attribute """
        XPATH = '@class'

    class TIMESTAMPS(MultiExtractor):
        """
        Paragraphs by classname that indicates timestamp-content
        """
        XPATH = './/p[re:test(@class, "^(RB|RE)")]'

    class HREF(SingleExtractor):
        """ Get href attribute """
        XPATH = '@href'

    class NAME(SingleExtractor):
        """ Get name attribute """
        XPATH = '@name'

    class TEXT(SingleExtractor):
        """ Get text element """
        XPATH = 'text()'

    class ALL_TEXT(SingleExtractor):
        @classmethod
        def xt(cls, el):
            return ST.strip_tags(el.extract())

    class RAWCONTENT(SingleExtractor):
        """
        Get raw content of all paragraphs (mainly for comparison to see if
        we missed something with the finer, paragaph-wise extraction).
        """
        @classmethod
        def xt(cls, response):
            textparts = []
            for txt in response.xpath('p'):
                textparts.append(txt.extract())
            return '\n\n'.join([' '.join(p.splitlines()) for p in textparts])

    class CONTENT_PLAIN(SingleExtractor):
        """
        Extract paragraphs that contain actual (speech) content (as opposed
        to elements that are empty, contain timestamps or are part of the
        footer of protocol-pages.
        TODO: paragraphs with RE are excluded, but sometimes it seems they
              contain actual text
        """
        @classmethod
        def _is_text(cls, response):
            pclass = None
            try:
                pclass = response.xpath('.//@class').extract().pop().strip()
            except:
                pass
            if pclass in DOCSECTIONS.PARAGRAPH_CLASSES or pclass is None:
                return True

        @classmethod
        def xt(cls, response):
            """
            Paragraphs by classname that indicates content of a statement.
            """
            return [t for t in response.xpath('p') if cls._is_text(t)]

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
    def paragraph(cls, p):
        """
        Pre-process a paragraph and replace comments and links with
        placeholders. Return resulting plain text, along with the
        replaced comments and links. Comments and links are each a list of
        tuples: (replace_text:str, replaced_element:Selector) .

        TODO: this method replaces I/comments first (before the links)
            that however means there might be a link inside a comment.
            this would have to be dealt with, e.g. by looking for markup in
            the replaced comments
        """
        html = p.extract()
        comments = []
        links = []
        for i, com in enumerate(p.xpath('.//i')):
            com_extract = com.extract()
            if ST.strip_tags(com_extract).startswith('('):
                repl = '[[com{}]]'.format(cls.replace_id)
                html = html.replace(com_extract, repl)
                comments.append((repl, com))
                cls.replace_id += 1
        for i, a in enumerate(p.xpath('.//a[@href]')):
            a_extract = a.extract()
            repl = '[[link{}]]'.format(cls.replace_id)
            html = html.replace(a_extract, repl)
            links.append((repl, a))
            cls.replace_id += 1

        return Paragraph(ST.strip_tags(html).strip(), links, comments)

    @classmethod
    def p_mkplain(cls, p, comments, links):
        """
        Build the final plain-text representation.
        For links, use only the text(); leave out comments entirely.
        """

        # Replace links
        for key, content in links:
            p = p.replace(key, cls.ALL_TEXT.xt(content))

        # Replace/clear the rest
        for match in regexAnnotation.findall(p):
            p = p.replace(match, '')

        return p

    @classmethod
    def p_mkannotate(cls, p, comments, links):
        """
        Build the final annotated (html) representation of a paragraph.
        """
        for key, content in comments:
            textel = minidom.Text()
            textel.data = cls.ALL_TEXT.xt(content)
            el = minidom.Element('i')
            el.setAttribute('class', 'comment')
            el.appendChild(textel)
            p = p.replace(key, el.toxml())

        for key, content in links:
            el = minidom.Element('a')
            el.setAttribute('class', 'ref')
            el.setAttribute('href', cls.HREF.xt(content))
            textel = minidom.Text()
            textel.data = cls.ALL_TEXT.xt(content)
            el.appendChild(textel)
            p = p.replace(key, el.toxml())

        return p

    @classmethod
    def get_speaker_role(cls, textpart):
        """
        Examining first word of textpart to get reference of speaker-role.
        """
        if textpart.startswith(u'Präs'):
            return cls.TAG_SPKR_ROLE_PRES
        elif textpart.startswith(u'Abg'):
            return cls.TAG_SPKR_ROLE_ABG
        else:
            return cls.TAG_SPKR_ROLE_OTHER

    @classmethod
    def merge_split_paragraphs(cls, textparts):
        """
        Re-merge paragraphs that have been divided by pagebreaks, footer lines etc.
        """
        merged = []
        for p in textparts:
            if len(p) and p[0].islower():
                pindx = len(merged) - 1
                if len(merged) and \
                   len(merged[pindx]) and merged[pindx][-1] == '-':
                    merged[pindx] = merged[pindx][0:-1]
                merged[pindx] += p
            else:
                merged.append(p)

        return [' '.join(p.splitlines()) for p in merged]

    @classmethod
    def detect_speaker(cls, plain, links):
        """
        Speaker information. If paragraph contains speaker header, return
        a tuple with (name, parl_id, role-tag, text_removed), otherwise False
        """
        try:
            match = regexSpeakerPart.findall(plain)[0]
            replacecode, link_selector = links[0]
            if replacecode in match:
                name = cls.ALL_TEXT.xt(link_selector)
                personlink = cls.HREF.xt(link_selector)
                ids = regexSpeakerId.findall(personlink)
                speaker_id = ids[0] if len(ids) else None
                role = cls.get_speaker_role(plain)
                replaced = plain.replace(match, '')
                return {"name":name, "id":speaker_id, "role": role,
                        "found": True, "cleaned": replaced}

        except IndexError:
            return {"found": False}

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
            stmt_links = []

            # Parse section
            classnames = cls.CLASSINFO.xt(item)
            timestamps = [ST.strip_tags(ts) for ts in cls.TIMESTAMPS.xt(item)]

            # P-looping, carry out annotations
            paragraphs = []
            speaker_candidates = []
            pinfos = []
            for pi, par in enumerate(cls.CONTENT_PLAIN.xt(item)):

                # Pre-process paragraph
                p = cls.paragraph(par)
                if p.plain == '':
                    continue

                # collect/append all links
                stmt_links += ([(cls.HREF.xt(a), cls.TEXT.xt(a))
                                for k, a in p.links])

                speakerdoc = cls.detect_speaker(p.plain, p.links)
                if speakerdoc['found']:
                    p.plain = speakerdoc['cleaned']
                    speaker_candidates.append((pi, speakerdoc))

                pinfos.append(p)

            # Attempt to re-merge paragraphs that were split up only by
            # page-breaks of the protocol
            plain_pars = cls.merge_split_paragraphs(
                [cls.p_mkplain(p.plain, p.comments, p.links) for p in pinfos])
            annotated_pars = cls.merge_split_paragraphs(
                [cls.p_mkannotate(p.plain, p.comments, p.links) for p in pinfos])

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

            res = {'raw_text': cls.RAWCONTENT.xt(item),
                   'full_text': "\n\n".join(plain_pars),
                   'annotated_text': "\n\n".join(annotated_pars),
                   'doc_section': classnames[0] if len(classnames) else None,
                   'links': stmt_links,
                   'timestamps': timestamps,
                   'ref_timestamp': current_timestamp,
                   'time_start': min(timestamps) if len(timestamps) else None,
                   'time_end': max(timestamps) if len(timestamps) else None,
                   'page_start': min(pages) if len(pages) else current_maxpage,
                   'page_end': max(pages) if len(pages) else current_maxpage,
                   }

            # If speaker parts have been identified (and they occured in
            # the first (0th) paragraph, use speaker info
            if len(speaker_candidates) and  speaker_candidates[0][0] == 0:
                res['text_type'] =  cls.TAG_STMT_REGULAR
                res['speaker_name'] = speaker_candidates[0][1]['name']
                res['speaker_id'] = speaker_candidates[0][1]['id']
                res['speaker_role'] = speaker_candidates[0][1]['role']
            else:
                res['text_type'] =  cls.TAG_STMT_OTHER
                res['speaker_name'] = None
                res['speaker_id'] = None
                res['speaker_role'] = None

            sections.append(res)
        return sections
