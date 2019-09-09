# -*- coding: utf-8 -*-
from ansicolor import green

from parlament.settings import BASE_HOST
from parlament.spiders import BaseSpider
from parlament.resources.extractors.llp import *

from op_scraper.models import LegislativePeriod


class LegislativePeriodSpider(BaseSpider):
    """
    The page with the select input element from where we get the list of
    LLPs seems to have moved one level deeper (to 'persons after year 1918')
    https://www.parlament.gv.at/WWER/PARL/J1918/
    # BASE_URL = "{}/{}".format(BASE_HOST, "/WWER/PARL/")
    """
    BASE_URL = "{}/{}".format(BASE_HOST, "/WWER/PARL/J1918/")

    name = "llp"
    title = "Legislative Periods Spider"

    ALLOWED_LLPS = []

    def __init__(self, **kw):
        super(LegislativePeriodSpider, self).__init__(**kw)

        self.start_urls = [self.BASE_URL]
        self.print_debug()

    def parse(self, response):

        llps = LLP.xt(response)

        for llp in llps:
            llp_item, created_llp = LegislativePeriod.objects.update_or_create(
                roman_numeral=llp['roman_numeral'],
                defaults=llp
            )
            llp_item.save()

            if created_llp:
                self.logger.info(u"Created Legislative Period {}".format(
                    green(u'[{}]'.format(llp['roman_numeral']))))
            else:
                self.logger.info(u"Updated Legislative Period {}".format(
                    green(u"[{}]".format(llp['roman_numeral']))
                ))
