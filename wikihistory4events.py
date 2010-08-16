#!/usr/bin/env python

##########################################################################
#                                                                        #
#  This program is free software; you can redistribute it and/or modify  #
#  it under the terms of the GNU General Public License as published by  #
#  the Free Software Foundation; version 2 of the License.               #
#                                                                        #
#  This program is distributed in the hope that it will be useful,       #
#  but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#  GNU General Public License for more details.                          #
#                                                                        #
##########################################################################

from datetime import date
import sys
import os
from random import random

## PROJECT LIBS
from sonet.mediawiki import HistoryPageProcessor, explode_dump_filename, \
     getTranslations, getTags
from sonet import lib

## DJANGO
os.environ['DJANGO_SETTINGS_MODULE'] = 'django_wikinetwork.settings'
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.append(PROJECT_ROOT+'/django_wikinetwork')
from django_wikinetwork.wikinetwork.models import WikiEvent
from django.db import transaction

class HistoryEventsPageProcessor(HistoryPageProcessor):
    accumulator = None

    def __init__(self, **kwargs):
        super(HistoryEventsPageProcessor, self).__init__(**kwargs)
        self.accumulator = []

    @transaction.commit_manually
    def flush(self):
        for page in self.accumulator:
            data = {'title': page['title'], 'lang': self.lang}
            we = WikiEvent(title=page['title'],
                           lang=self.lang,
                           talk=(page['type'] == 'talk'),
                           data=page['counter'],
                           desired=page['desired'])
            we.save()
            del data, page, we
        transaction.commit()
        del self.accumulator
        self.accumulator = []

    def save_in_django_model(self):
        data = {
            'title': self._title,
            'type': self._type,
            'desired': self._desired,
            'counter': self._counter
        }

        self.accumulator.append(data)
        self.counter_pages += 1

    def process_timestamp(self, elem):
        if self._skip: return

        tag = self.tag

        timestamp = elem.text
        year = int(timestamp[:4])
        month = int(timestamp[5:7])
        day = int(timestamp[8:10])
        revision_time = date(year, month, day)

        days = (revision_time - self.s_date).days
        self._counter[days] = self._counter.get(days, 0) + 1

        del days, revision_time
        self.count += 1
        if not self.count % 50000:
            self.flush()
            print 'PAGES:', self.counter_pages, 'REVS:', self.count


def main():
    import optparse

    p = optparse.OptionParser(usage="usage: %prog [options] file desired_list acceptance_ratio")
    _, files = p.parse_args()

    if len(files) != 3:
        p.error("Wrong parameters")

    xml = files[0]
    desired_pages_fn = files[1]
    threshold = float(files[2])

    with open(desired_pages_fn) as f:
        lines = f.readlines()

    desired_pages = [l.decode('latin-1') for l in [l.strip() for l in lines]
                     if l and not l[0] == '#']

    lang, _, _ = explode_dump_filename(xml)

    deflate, _lineno = lib.find_open_for_this_file(xml)

    if _lineno:
        src = deflate(xml, 51)
    else:
        src = deflate(xml)

    translation = getTranslations(src)
    tag = getTags(src, tags='page,title,revision,'+ \
                  'minor,timestamp,redirect')

    src.close()
    src = deflate(xml)

    processor = HistoryEventsPageProcessor(tag=tag, lang=lang)
    processor.talkns = translation['Talk']
    processor.threshold = threshold
    processor.set_desired(desired_pages)

    print "BEGIN PARSING"
    processor.start(src)
    processor.flush()


if __name__ == "__main__":
    #import cProfile as profile
    #profile.run('main()', 'mainprof')
    main()