"""
This file was generated with the customdashboard management command and
contains the class for the main dashboard.

To activate your index dashboard add the following to your settings.py::
    GRAPPELLI_INDEX_DASHBOARD = 'offenesparlament.op_scraper_dashboard.CustomIndexDashboard'
"""

from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse

from grappelli.dashboard import modules, Dashboard
from grappelli.dashboard.utils import get_admin_site_name


class CustomIndexDashboard(Dashboard):

    """
    Custom index dashboard for www.
    """

    def init_with_context(self, context):
        site_name = get_admin_site_name(context)

        # append a group for "Administration" & "Applications"
        # self.children.append(modules.Group(
        #     _('Group: Administration & Applications'),
        #     column=1,
        #     collapsible=True,
        #     children=[
        #         modules.AppList(
        #             _('Administration'),
        #             column=1,
        #             collapsible=False,
        #             models=('django.contrib.*',),
        #         ),
        #         modules.AppList(
        #             _('Applications'),
        #             column=1,
        #             css_classes=('collapse closed',),
        #             exclude=('django.contrib.*',),
        #         )
        #     ]
        # ))

        # append an app list module for "Applications"
        self.children.append(modules.AppList(
            _('AppList: Applications'),
            collapsible=True,
            column=1,
            css_classes=('collapse closed',),
            exclude=('django.contrib.*',),
        ))

        # append an app list module for "Administration"
        self.children.append(modules.ModelList(
            _('ModelList: Administration'),
            column=1,
            collapsible=True,
            models=('django.contrib.*',),
        ))

        # append another link list module for "support".
        self.children.append(modules.LinkList(
            _('Scraping Management'),
            column=2,
            children=[
                {
                    'title': _('Scrape Legislative Periods'),
                    'url': '/admin/scrape/llp',
                    'external': False,
                },
                {
                    'title': _('Scrape Persons'),
                    'url': '/admin/scrape/persons',
                    'external': False,
                },
                {
                    'title': _('Scrape Persons/Administrations'),
                    'url': '/admin/scrape/administrations',
                    'external': False,
                },
                {
                    'title': _('Scrape Persons/Audit Office Presidents'),
                    'url': '/admin/scrape/auditors',
                    'external': False,
                },
                {
                    'title': _('Scrape Pre-Laws'),
                    'url': '/admin/scrape/pre_laws',
                    'external': False,
                },
                {
                    'title': _('Scrape Laws'),
                    'url': '/admin/scrape/laws',
                    'external': False,
                },
                {
                    'title': _('Scrape Inquiries'),
                    'url': '/admin/scrape/inquiries',
                    'external': False,
                },
                {
                    'title': _('Scrape Petitions'),
                    'url': '/admin/scrape/petitions',
                    'external': False,
                },
                {
                    'title': _('Scrape Debates/Statements'),
                    'url': '/admin/scrape/debates',
                    'external': False,
                },
            ]
        ))

        self.children.append(modules.LinkList(
            _('ElasticSearch'),
            column=2,
            children=[
                {
                    'title': _('Update ElasticSearch Index'),
                    'url': '/admin/elastic/update',
                    'external': False,
                },
            ]
        ))

        # append another link list module for "support".
        # self.children.append(modules.LinkList(
        #     _('Support'),
        #     column=2,
        #     children=[
        #         {
        #             'title': _('Django Documentation'),
        #             'url': 'http://docs.djangoproject.com/',
        #             'external': True,
        #         },
        #         {
        #             'title': _('Grappelli Documentation'),
        #             'url': 'http://packages.python.org/django-grappelli/',
        #             'external': True,
        #         },
        #         {
        #             'title': _('Grappelli Google-Code'),
        #             'url': 'http://code.google.com/p/django-grappelli/',
        #             'external': True,
        #         },
        #     ]
        # ))

        #append a feed module
        # self.children.append(modules.Feed(
        #     _('Latest Django News'),
        #     column=2,
        #     feed_url='http://www.djangoproject.com/rss/weblog/',
        #     limit=5
        # ))

        # append a recent actions module
        self.children.append(modules.RecentActions(
            _('Recent Actions'),
            limit=5,
            collapsible=True,
            column=2,
        ))
