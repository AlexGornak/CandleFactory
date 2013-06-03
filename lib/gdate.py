#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       gdate.py
#       gdate - widget and functions for calendar dates
#       Copyright 2012 New Systems Telecom, 2012
#       Developer: Alexander Gornak <ag@nstel.ru>
#
#
#

import time
import math
import pygtk
pygtk.require('2.0')
import gtk
import gobject
from prmc import *


def start_of_day(t):
    ts=time.localtime(t)
    dt=3600*ts.tm_hour+60*ts.tm_min+ts.tm_sec
    return(int(t-dt))

def start_of_week(t):
    ts=time.localtime(t)
    dt=3600*24*ts.tm_wday+3600*ts.tm_hour+60*ts.tm_min+ts.tm_sec
    return(int(t-dt))

def mktime(d, m, y):
    t=time.mktime((y, m, d, 0, 0, 0, 0, 0, 0))
    return(t)

def mondays(m, y):
    t=mktime(1, m, y)
    ts=time.localtime(t)
    if ts.tm_wday==0: mon=1
    else: mon=8-ts.tm_wday
    d_in_m=days_in_month(m, y)
    m=[]
    while mon <= d_in_m:
        m.append(mon)
        mon+=7
    return(m)

mdays=[31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
def days_in_month(month, year):
    d=mdays[month-1]
    if (month==2) and (year%4==0): d+=1
    return(d)

################################################################################
monthes=['январь', 'февраль', 'март', 'апрель', 'май', 'июнь', \
         'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь']

class GDate(gtk.HBox):
    def __init__(self, interval=ONE_DAY):
        super(GDate, self).__init__(spacing=2)
        ct=time.time()
        ts=time.localtime(ct)
        self.dd=ts.tm_mday
        self.mm=ts.tm_mon
        self.yy=ts.tm_year

        self.dstore=gtk.ListStore(gobject.TYPE_INT)
        self.d_cb=gtk.ComboBox(self.dstore)
        cell=gtk.CellRendererText()
        self.d_cb.pack_start(cell, True)
        self.d_cb.add_attribute(cell, 'text', 0)
        self.pack_start(self.d_cb, expand=False, padding=4)
        for d in range(days_in_month(self.mm, self.yy)):
            self.dstore.append([d+1])
        self.d_cb.set_active(self.dd-1)

        mstore=gtk.ListStore(gobject.TYPE_STRING)
        self.m_cb=gtk.ComboBox(mstore)
        cell=gtk.CellRendererText()
        self.m_cb.pack_start(cell, True)
        self.m_cb.add_attribute(cell, 'text', 0)
        for m in monthes:
            mstore.append([m])
        self.pack_start(self.m_cb, expand=False, padding=4)
        self.m_cb.set_active(self.mm-1)
        self.m_cb.connect("changed", self._changed, 1)

        ystore=gtk.ListStore(gobject.TYPE_INT)
        y_cb=gtk.ComboBox(ystore)
        cell=gtk.CellRendererText()
        y_cb.pack_start(cell, True)
        y_cb.add_attribute(cell, 'text', 0)
        for i in range(10):
            ystore.append([i+2012])
        self.pack_start(y_cb, expand=False, padding=4)
        y_cb.set_active(self.yy-2012)
        y_cb.connect("changed", self._changed, 2)

        self.set_interval(interval)
        self.show_all()

    def get_time(self):
        i=self.d_cb.get_active()
        if self.interval==ONE_WEEK:
            dd=self.mds[i]
        else: dd=i+1
        return(mktime(dd, self.mm, self.yy))

    def set_interval(self, interval):
        if interval==ONE_DAY or interval==ONE_WEEK:
            self.d_cb.set_property("sensitive", True)
            self.m_cb.set_property("sensitive", True)
            if interval==ONE_WEEK:
                self.dstore.clear()
                self.mds=mondays(self.mm, self.yy)
                for d in self.mds:
                    self.dstore.append([d])
            else:
                self.dstore.clear()
                for d in range(days_in_month(self.mm, self.yy)):
                    self.dstore.append([d+1])
            self.d_cb.set_active(0)
        elif interval==ONE_MONTH:
            self.dd=1
            self.d_cb.set_active(self.dd-1)
            self.d_cb.set_property("sensitive", False)
            self.m_cb.set_property("sensitive", True)
        elif interval==ONE_YEAR:
            self.dd=1
            self.d_cb.set_active(self.dd-1)
            self.d_cb.set_property("sensitive", False)
            self.mm=1
            self.m_cb.set_active(self.mm-1)
            self.m_cb.set_property("sensitive", False)
        self.interval=interval

    def update_day(self):
        if self.interval==ONE_WEEK:
            self.dstore.clear()
            self.mds=mondays(self.mm, self.yy)
            for d in self.mds:
                self.dstore.append([d])
            self.d_cb.set_active(0)
        else:
            day=self.d_cb.get_active()+1
            maxday=days_in_month(self.mm, self.yy)
            if day>maxday: day=maxday
            self.dstore.clear()
            for i in range(maxday):
                self.dstore.append([i+1])
            self.d_cb.set_active(day-1)

    def _changed(self, cbwidget, param):
        if param==1:
            self.mm=cbwidget.get_active()+1
        elif param==2:
            self.yy=cbwidget.get_active()+2012
        self.update_day()



################################################################################

if __name__ == "__main__":
    win = gtk.Window()
    win.connect('destroy', gtk.main_quit)
    gdate = GDate(ONE_WEEK)
    win.add(gdate)
    win.show_all()

    gtk.main()

