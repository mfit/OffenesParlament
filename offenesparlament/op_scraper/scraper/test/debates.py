# -*- coding: utf-8 -*-
import unittest
import os
from io import open
import urllib2
from scrapy import Selector
from scrapy.http import Request
from parlament.resources.extractors.statement import regexSpeakerPart
from parlament.resources.extractors.statement import DOCSECTIONS

def open_or_fetch(fname, debate_url):
    try:
        with open(fname, encoding='windows-1252') as f:
                return f.read()
    except:
        response = urllib2.urlopen(debate_url)
        html = response.read().decode('windows-1252')
        with open(fname, 'w', encoding='windows-1252') as f:
            f.write(html)
        return html

class TestParseDebateXV51(unittest.TestCase):
    """ Tests docsections extractor with parsing a complete debate protocol """

    def setUp(self):
        self.maxDiff = None
        debate_url = "https://www.parlament.gv.at/PAKT/VHG/XXV/NRSITZ/NRSITZ_00051/fnameorig_385039.html"
        fname = os.path.join(os.path.dirname(__file__), 'cache', 'NRSITZ_00051.html')
        content = open_or_fetch(fname, debate_url)
        self.doc = Selector(text=content)

    def test_document_read_successfully(self):
        self.assertEquals(len(self.doc.xpath('//div')), 489,
                          "the number of divs is 489")

    def test_parse_statement_classification(self):
        sections = DOCSECTIONS.xt(self.doc)

        self.assertEquals(len([s for s in sections if s['text_type'] == 'other']),
                          24, "Expects 24 'other' sections")
        self.assertEquals(len([s for s in sections if s['text_type'] == 'reg']),
                          462, "Expects 462 regular sections")

        self.assertEquals(len([s for s in sections if s['speaker_role'] == 'other']),
                          44, "Expects 44 unclassified statements")
        self.assertEquals(len([s for s in sections if s['speaker_role'] == 'pres']),
                          244, "Expects 244 statements by president")
        self.assertEquals(len([s for s in sections if s['speaker_role'] == 'abg']),
                          174, "Expects 174 statements by members")

    def test_plaintext_extraction(self):
        unicode_firstp = u"""Für diese Sitzung hat das Bundeskanzleramt über Vertretung von Mitgliedern der Bundesregierung folgende Mitteilungen gemacht:"""
        unicode_secondp = u"""Die Bundesministerin für Familien und Jugend Dr. Sophie Karmasin wird durch die Bundesministerin für Inneres Mag. Johanna Mikl-Leitner vertreten."""
        sections = DOCSECTIONS.xt(self.doc)
        section = sections[3]
        paragraphs = section['full_text'].split('\n\n')
        self.assertEquals(len(paragraphs), 5, "Statement contains 5 paragraphs")
        self.assertEquals(paragraphs[0], unicode_firstp)
        self.assertEquals(paragraphs[1], unicode_secondp)

    def test_annotatedtext_extraction(self):
        unicode_firstp = u"""Für diese Sitzung hat das Bundeskanzleramt über Vertretung von Mitgliedern der Bundesregierung folgende Mitteilungen gemacht:"""
        unicode_secondp = u"""Die Bundesministerin für Familien und Jugend Dr. Sophie Karmasin wird durch die Bundesministerin für Inneres <a class="ref" href="/WWER/PAD_08214/index.shtml">Mag. Johanna Mikl-Leitner</a> vertreten."""
        sections = DOCSECTIONS.xt(self.doc)
        section = sections[3]
        paragraphs = section['annotated_text'].split('\n\n')
        self.assertEquals(len(paragraphs), 5, "Statement contains 5 paragraphs")
        self.assertEquals(paragraphs[0], unicode_firstp)
        self.assertEquals(paragraphs[1], unicode_secondp)

class TestParseDebateXIII49(unittest.TestCase):
    """ Tests docsections extractor with parsing a complete debate protocol """
    def setUp(self):
        self.maxDiff = None
        debate_url = "https://www.parlament.gv.at/PAKT/VHG/XXIII/NRSITZ/NRSITZ_00049/fnameorig_115155.html"
        fname = os.path.join(os.path.dirname(__file__), 'cache', 'NRSITZ_00049.html')
        content = open_or_fetch(fname, debate_url)
        self.doc = Selector(text=content)

    def test_document_read_successfully(self):
        self.assertEquals(len(self.doc.xpath('//div')), 104,
                          "the number of divs is 104")

    def test_parse_statement_classification(self):
        sections = DOCSECTIONS.xt(self.doc)

        self.assertEquals(len([s for s in sections if s['text_type'] == 'other']),
                          17, "Expects 24 'other' sections")
        self.assertEquals(len([s for s in sections if s['text_type'] == 'reg']),
                          84, "Expects 462 regular sections")

        self.assertEquals(len([s for s in sections if s['speaker_role'] == 'other']),
                          4, "Expects 44 unclassified statements")
        self.assertEquals(len([s for s in sections if s['speaker_role'] == 'pres']),
                          54, "Expects 244 statements by president")
        self.assertEquals(len([s for s in sections if s['speaker_role'] == 'abg']),
                          26, "Expects 174 statements by members")

    def test_plaintext_extraction(self):
        unicode_firstp = u"""Meine sehr verehrten Damen und Herren!  Herr Bundesminister! Wir haben jetzt von Ihnen 28 Antworten auf 28 Fragen  die niemand gestellt hat, erhalten. Die 28 Fra­gen, die Sie nicht beantwortet haben, werden Sie ein zweites Mal beantworten können, und zwar im parlamentarischen Untersuchungsausschuss. """
        unicode_lastp = u"""Deshalb sehe ich den Untersuchungssausschuss als eine der größten politischen Chancen dieser Republik  und hoffe, dass dieses Haus diese Chance nützt. – Danke schön. """
        sections = DOCSECTIONS.xt(self.doc)
        section = sections[14]
        paragraphs = section['full_text'].split('\n\n')
        self.assertEquals(len(paragraphs), 28, "Statement contains 28 paragraphs")
        self.assertEquals(paragraphs[0], unicode_firstp)
        self.assertEquals(paragraphs[27], unicode_lastp)

    def test_annotatedtext_extraction(self):
        unicode_firstp = u"""Meine sehr verehrten Damen und Herren!  Herr Bundesminister! Wir haben jetzt von Ihnen 28 Antworten auf 28 Fragen <i class="comment">(Abg. Mag. Donnerbauer: Das sind Fakten!),</i> die niemand gestellt hat, erhalten. Die 28 Fra­gen, die Sie nicht beantwortet haben, werden Sie ein zweites Mal beantworten können, und zwar im parlamentarischen Untersuchungsausschuss. <i class="comment">(Beifall bei den Grünen. – Zwischenrufe bei der ÖVP.)</i>"""
        unicode_lastp = u"""Deshalb sehe ich den Untersuchungssausschuss als eine der größten politischen Chancen dieser Republik <i class="comment">(Zwischenruf des Abg. Großruck)</i> und hoffe, dass dieses Haus diese Chance nützt. – Danke schön. <i class="comment">(Beifall bei den Grünen. – Abg. Neuge­bauer: Vorverurteiler!)</i>"""

        sections = DOCSECTIONS.xt(self.doc)
        section = sections[14]
        paragraphs = section['annotated_text'].split('\n\n')
        self.assertEquals(len(paragraphs), 28)
        self.assertEquals(paragraphs[0], unicode_firstp)
        self.assertEquals(paragraphs[27], unicode_lastp)


class TestDocsectionsParagraphs(unittest.TestCase):

    def test_detect_speaker_abgeordneter(self):
        abg_paragraph = u"""<p class=MsoNormal style='margin-top:.70em;margin-right:0cm;margin-bottom:.70em; margin-left:0cm'><b><span lang=DE style='display:none'><!--†--></span>Abgeordneter
<A HREF="/WWER/PAD_12907/index.shtml">Fritz&nbsp;Grillitsch</A></b> (&Ouml;VP)<span style='display:none'><!--¦--></span>: Herr <span lang=DE>Bundesminister,
ich bin dir sehr dankbar, dass du aufgrund deiner Produktion in &Ouml;ster&shy;reich.&nbsp;&#8211; Herzlichen Dank
daf&uuml;r. <i>(Abg. <b>Neubauer</b>&nbsp;&#8211; in Richtung &Ouml;VP, eine entsprechen&shy;de Handbewegung andeutend&nbsp;&#8211;:
Klatschen!)</i></span></p>
"""
        par = Selector(text=abg_paragraph).xpath('.//p')[0]
        p = DOCSECTIONS.paragraph(par)

        speaker = DOCSECTIONS.detect_speaker(p.plain, p.links)
        self.assertEqual(speaker['found'], True)
        self.assertEqual(speaker['id'], 'PAD_12907')
        self.assertEqual(speaker['role'], 'abg')


    def test_detect_speaker_minister_simple(self):
        abg_paragraph = u"""<p class=MsoNormal style='margin-top:.70em;margin-right:0cm;margin-bottom:.70em; margin-left:0cm'><b><span lang=DE style='display:none'><!--†--></span>Bundesminister f&uuml;r Land- und Forstwirtschaft,
Umwelt und Wasserwirtschaft <A HREF="/WWER/PAD_83296/index.shtml">Ing.&nbsp;Andr&auml;&nbsp;Rupprechter</A></b>: Herr <span lang=DE>Bundesminister,
ich bin dir sehr dankbar, dass du aufgrund deiner Produktion in &Ouml;ster&shy;reich.&nbsp;&#8211; Herzlichen Dank
daf&uuml;r. <i>(Abg. <b>Neubauer</b>&nbsp;&#8211; in Richtung &Ouml;VP, eine entsprechen&shy;de Handbewegung andeutend&nbsp;&#8211;:
Klatschen!)</i></span></p>
"""
        par = Selector(text=abg_paragraph).xpath('.//p')[0]
        p = DOCSECTIONS.paragraph(par)

        speaker = DOCSECTIONS.detect_speaker(p.plain, p.links)
        self.assertEqual(speaker['found'], True)
        self.assertEqual(speaker['id'], 'PAD_83296')
        self.assertEqual(speaker['role'], 'other')


    def test_detect_speaker_minister(self):
        # This paragraph has invalid HTML around the speaker link, and
        # only part of the speaker-name+title is enclosed by the link
        paragraph = u"""<p class=MsoNormal><b><span lang=DE style='display:none;letter-spacing:-.2pt'><!--†--></span><span style='letter-spacing:-.2pt'>Bundesminister f&uuml;r Land- und Forstwirtschaft,
Umwelt und Wasserwirtschaft <A HREF="/WWER/PAD_83296/index.shtml">Dipl.-</span>Ing.&nbsp;Andr&auml;&nbsp;Rupprechter</A><span style='display:none'><!--¦--></span>:</b> Grunds&auml;tzlich ist neben dem Heimmarkt
der Exportmarkt au&szlig;erordentlich wichtig f&uuml;r die <span lang=DE>&ouml;sterreichische
Landwirtschaft, Lebensmittelwirtschaft, weshalb wir uns gerade auch aufgrund
der Russland-Krise letztes Jahr bem&uuml;ht haben, zus&auml;tzliche neue
Drittlandm&auml;rkte zu finden. Und das ist tats&auml;chlich gelungen: Der agra&shy;rische
Au&szlig;enhandel hat sich im Jahr&nbsp;2014 trotz der sehr schwierigen
Wirtschafts&shy;bedingungen positiv entwickelt, weist immerhin ein Plus von
2,4&nbsp;Prozent gegen&uuml;ber 2013 auf, trotz des Wegfalls des so wichtigen
Marktes in Russland.</span></p>
"""
        par = Selector(text=paragraph).xpath('.//p')[0]
        p = DOCSECTIONS.paragraph(par)

        # print(plain)
        speaker = DOCSECTIONS.detect_speaker(p.plain, p.links)
        # self.assertEqual(speaker['found'], True)
        # self.assertEqual(speaker['id'], 'PAD_12907')
        # self.assertEqual(speaker['role'], 'abg')



