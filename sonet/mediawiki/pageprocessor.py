#import xml.etree.cElementTree as etree
from lxml import etree
from datetime import date
from random import random

class PageProcessor(object):
    count = 0
    count_archive = 0
    ecache = None
    tag = None
    user_talk_names = None
    search = None
    lang = None

    def __init__(self, ecache=None, tag=None, user_talk_names=None,
                 search=None, lang=None):
        self.ecache = ecache
        self.tag = tag
        self.user_talk_names = user_talk_names
        self.search = search
        self.lang = lang

    def start(self, f):
        import inspect
        dfunc = {}

        ## FIND PROCESS METHODS
        for member_name, type_ in inspect.getmembers(self):
            if not member_name.startswith('process_'): continue
            member = self.__getattribute__(member_name)
            if not inspect.ismethod(member): continue
            dfunc[self.tag[member_name[8:]]] = member

        context = etree.iterparse(f)
        for elem in (elem for _, elem in context if elem.tag in dfunc):
            dfunc[elem.tag](elem)
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
        del context


class HistoryPageProcessor(PageProcessor):
    counter_pages = 0
    ## desired pages
    desired_pages = None
    ## initial date, used for comparison and substraction
    s_date = date(2000, 1, 1)
    _counter = None
    _title = None
    _type = None
    ## Whether the page should be skipped or not, according to its Namespace
    _skip = None
    threshold = 1.
    talkns = None
    _desired = False

    def set_desired(self, l):
        self.desired_pages = set(l)

    def is_desired(self, title):
        return (title in self.desired_pages)

    def delattr(self, attrs):
        for attr in attrs:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def process_title(self, elem):
        self.delattr(("_counter", "_type", "_title", "_skip"))
        self._skip = False

        a_title = elem.text.split(':')
        if len(a_title) == 1:
            self._type = 'normal'
            self._title = a_title[0]
        else:
            if a_title[0] == self.talkns:
                self._type = 'talk'
                self._title = a_title[1]
            else:
                self._skip = True
                return

        #print self._title, self._title == 'Venesia'
        self._desired = self.is_desired(self._title)
        if not self._desired and self.threshold < 1.:
            if self.threshold == 0. or random() > self.threshold:
                self._skip = True
                return

        self._counter = {}

    def process_page(self, _):
        if not self._skip:
            self.save_in_django_model()

    def process_redirect(self, _):
        self._skip = True