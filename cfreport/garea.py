#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       garea.py
#       garea - widget for drawing of graphics
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
import cairo
from prmc import *

def start_of_day(t):
    ts=time.localtime(t)
    dt=3600*ts.tm_hour+60*ts.tm_min+ts.tm_sec
    return(int(t-dt))
################################################################################
MIN_WIDTH=500
MIN_HIGHT=300
DASH_SIZE=5.0
VSTEPS=10.0
################################################################################
class VRuler(gtk.DrawingArea):
    def __init__(self, v0, v1, vunit=''):
        super(VRuler, self).__init__()
        self.vunit=vunit
        self._span=(v1, v0)
        self._pos=0
        self.connect("expose-event", self.on_expose)
        self.connect_after("realize", self.on_realize)

    def on_realize(self, widget):
        cr = widget.window.cairo_create()
        cr.save()
        cr.select_font_face('sans-serif')
        cr.set_font_size(10)
        cr.set_line_width(1.0)
        st0="%.2f" % (self._span[0]*100)  #assume 2 order will be enough
        st1="%.2f" % (self._span[1]*100)
        (ww0, hh0)=cr.text_extents(st0)[2:4]
        (ww1, hh1)=cr.text_extents(st1)[2:4]
        cr.restore()
        w=max(ww0, ww1)+DASH_SIZE+2.0
        self.set_size_request(int(w), -1)
    
    def draw(self, cr, w, h):
        vstep=(self._span[1]-self._span[0])/VSTEPS
        cr.save()
        cr.select_font_face('sans-serif')
        cr.set_font_size(10)
        cr.set_source_rgb(0.0, 0.0, 1.0)
        cr.set_line_width(1.0)
        step_in_pix=float(h)/VSTEPS
        cr.move_to(w-1, 0)
        cr.rel_line_to(0, h)
        (ww, hh)=cr.text_extents(self.vunit)[2:4]
        cr.move_to(w-ww-2.0, hh+2.0)
        cr.show_text(self.vunit)
        y=step_in_pix
        v0=self._span[0]+vstep
        while y<(h-1):
            cr.move_to(w, y)
            cr.rel_line_to(-DASH_SIZE, 0)
            st0="%.2f" % v0
            (ww, hh)=cr.text_extents(st0)[2:4]
            cr.move_to(w-DASH_SIZE-ww-1.0, y+hh/2)
            cr.show_text(st0)
            v0+=vstep
            y+=step_in_pix
        cr.stroke()
        cr.set_dash([2.0, 3.0])
        cr.move_to(0, self._pos)
        cr.rel_line_to(w, 0)
        cr.stroke()
        cr.restore()
        
    def on_expose(self, widget, event):
        cr = widget.window.cairo_create()
        w=widget.allocation.width
        h=widget.allocation.height
        self.draw(cr, w, h)
        return False

    @property
    def span(self):
        return self._span
    @span.setter
    def span(self, value):
        self._span=value
        self.queue_draw()

    @property
    def pos(self):
        return self._pos
    @pos.setter
    def pos(self, newpos):
        self._pos=newpos
        self.queue_draw()
################################################################################
#time periods constants (in seconds)
_10MIN = 600
_30MIN = 1800
_1HOUR = 3600
_4HOUR = 14400
_12HOUR = 43200
_1DAY = 86400
_1WEEK = 604800
_1MONTH = 2678400  #31 days
_1YEAR = 31622400  #366 days
#period, step, format, sample
TMODELS=[(TEN_MIN, 60, "%H:%M", "00:00"),
         (THIRTY_MIN, 300, "%H:%M", "00:00"),
         (ONE_HOUR, 600, "%H:%M", "00:00"),
         (FOUR_HOUR, 1800, "%H:%M", "00:00"),
         (TWENTY_HOUR, 3600, "%H:%M", "00:00"),
         (ONE_DAY, 7200, "%H:%M", "00:00"),
         (ONE_WEEK, 86400, "%d.%m", "00.00"),
         (ONE_MONTH, 86400, "%d.%m", "00.00"),
         (ONE_YEAR, 2635200, "%d.%m", "00.00")]

class TRuler(gtk.DrawingArea):
    def __init__(self, tstart=None, tperiod=TEN_MIN):
        super(TRuler, self).__init__()
         
        self.type=0
        for tm in TMODELS:
            if tperiod<=tm[0]:
                break
            self.type+=1
        self.tsetup()
        if tstart is None:
            self._t1=time.time()
            self._t0=self._t1-self._tperiod
        else:
            self._t0=tstart
            self._t1=self._t0+self._tperiod
        if self._tperiod>=_1WEEK:
            self._t0=start_of_day(self._t0)
            self._t1=self._t0+self._tperiod

        self._pos=0    
        self.connect("expose-event", self.on_expose)
        self.connect_after("realize", self.on_realize)

    def tsetup(self):
        self._tperiod=TMODELS[self.type][0]
        self._tstep=TMODELS[self.type][1]
        self._tformat=TMODELS[self.type][2]
        self._tsample=TMODELS[self.type][3]
        
    def on_realize(self, widget):
        cr = widget.window.cairo_create()
        cr.save()
        cr.select_font_face('sans-serif')
        cr.set_font_size(10)
        cr.set_line_width(1.0)
        (self.ww, self.hh)=cr.text_extents(self._tsample)[2:4]
        cr.restore()
        #self.step_in_pix=ww*1.5
        h=DASH_SIZE+2*self.hh+7.0
        self.set_size_request(-1, int(h))
   
    def draw(self, cr, w, h):
        cr.save()
        cr.select_font_face('sans-serif')
        cr.set_font_size(10)
        cr.set_source_rgb(0.0, 0.0, 1.0)
        cr.set_line_width(1.0)
        cr.move_to(0, 1)
        cr.rel_line_to(w, 0)
        ts=time.localtime(self._t0)
        tstr=time.strftime("%d.%m.%y", ts)
        cr.move_to(0, DASH_SIZE+2*self.hh+4.0)
        cr.show_text(tstr)
        scx=float(w)/float(self._tperiod)
        cstep=self._tstep
        while scx*cstep<self.ww:
            cstep+=self._tstep
        px=0
        if ts.tm_sec:
            ct=int(self._t0+60-ts.tm_sec)
        else:
            ct=int(self._t0+self._tstep)
        while ct<self._t0+self._tperiod:
            x=scx*(ct-self._t0)
            dx=x-px
            if x>0:
                cr.move_to(x, 0)
                cr.rel_line_to(0, DASH_SIZE)
            if dx>=self.ww/2.0:
                tstr=time.strftime(self._tformat, time.localtime(ct))
                (ww, hh)=cr.text_extents(tstr)[2:4]
                cr.move_to(x-ww/2.0, DASH_SIZE+hh+2.0)
                cr.show_text(tstr)
            px=x
            ct+=cstep
        cr.stroke()
        cr.set_dash([2.0, 3.0])
        cr.move_to(self._pos, 0)
        cr.rel_line_to(0, h)
        cr.stroke()
        cr.restore()
        
    def on_expose(self, widget, event):
        cr = widget.window.cairo_create()
        w=widget.allocation.width
        h=widget.allocation.height
        self.draw(cr, w, h)
        return False

    @property
    def pos(self):
        return self._pos
    @pos.setter
    def pos(self, newpos):
        self._pos=newpos
        self.queue_draw()

    @property
    def t0(self):
        return self._t0

    @property
    def t1(self):
        return self._t1
    @t1.setter
    def t1(self, _t1):
        self._t1=_t1
        self._t0=self._t1-self._tperiod
        self.queue_draw()
    
################################################################################    

def get_minmax(ga):
    v0, v1=None, None
    for g in ga:
        if v0 is None:
            v0, v1=g[1], g[1]
        elif g[1]<v0: v0=g[1]
        elif g[1]>v1: v1=g[1]
    if v0 is None: v0, v1=-10000.0, 10000.0    #it's no good
    return((v0, v1))

class GArea(gtk.Table):
    def __init__(self, _ga=None, _vunit='', _tstart=None, _tperiod=TEN_MIN):
        super(GArea, self).__init__(2, 2)
        self.attach(gtk.DrawingArea(), 0, 1, 1, 2, gtk.FILL, gtk.FILL)
        self.ga=_ga
        self.ga1=None
        if _ga is None: (v0, v1)=(-10000.0, 10000.0)
        else:
            (v0, v1)=get_minmax(_ga)
            v0-=0.1*math.fabs(0.5*(v0+v1))
            v1+=0.1*math.fabs(0.5*(v0+v1))
        self.vruler=VRuler(v0, v1, _vunit)
        self.truler=TRuler(tstart=_tstart, tperiod=_tperiod)
        self.darea=gtk.DrawingArea()
        self.darea.modify_bg(gtk.STATE_NORMAL, gtk.gdk.Color(1.0, 1.0, 1.0))
        self.darea.connect("expose-event", self.on_expose)
        self.darea.connect("motion-notify-event", self.on_mouse_motion)
        self.darea.connect("button-press-event", self.on_mouse_button)
        self.darea.connect("scroll-event", self.on_scroll)
        self.darea.add_events(gtk.gdk.POINTER_MOTION_MASK
                              | gtk.gdk.BUTTON_PRESS_MASK
                              | gtk.gdk.BUTTON1_MOTION_MASK
                              | gtk.gdk.SCROLL_MASK
                              )

        self.darea.set_size_request(MIN_WIDTH, MIN_HIGHT)
        self.attach(self.vruler, 0, 1, 0, 1, gtk.FILL, gtk.EXPAND | gtk.FILL)
        self.attach(self.truler, 1, 2, 1, 2, gtk.EXPAND | gtk.FILL, gtk.FILL)
        self.attach(self.darea, 1, 2, 0, 1, gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL)

    def set_ref_dict(self, interval_i, rp_i, rv_i):
        self.ref={'interval': interval_i, 'regpoint': rp_i, 'regvalue': rv_i}
        
    def on_expose(self, widget, event):
        cr = widget.window.cairo_create()
        w=widget.allocation.width
        h=widget.allocation.height
        self.calc_matrix(w, h)
        if self.ga is not None:
            self.draw(cr, self.ga, 0.5, 0.1, 0.1)
            if self.ga1 is not None:
                self.draw(cr, self.ga1, 0.0, 1.0, 0.0)
        return True

    def on_mouse_motion(self, widget, event):
        self.truler.pos=event.x
        self.vruler.pos=event.y
        x, y = event.x, event.y
        if event.state & gtk.gdk.BUTTON1_MASK:
            dx, dy = x-self.panx, y-self.pany
            self.panx, self.pany = x, y
            (v1, v0)=self.vruler.span
            v0-=dy/self.scy
            v1-=dy/self.scy
            self.vruler.span=(v1, v0)
            widget.queue_draw()
        return True
        
    def on_mouse_button(self, widget, event):
        if event.button==1:
            self.panx, self.pany = event.x, event.y
        return True
        
    def on_scroll(self, widget, event):
        if event.direction==gtk.gdk.SCROLL_DOWN:
            k=0.1
        elif event.direction==gtk.gdk.SCROLL_UP:
            k=-0.1
        (v1, v0)=self.vruler.span
        dv=v1-v0
        v0+=k*dv
        v1-=k*dv
        self.vruler.span=(v1, v0)
        widget.queue_draw()
        return True

    
    def calc_matrix(self, w, h):
        (v1, v0)=self.vruler.span
        self.t0, t1 = self.truler.t0, self.truler.t1
        self.scx=float(w)/(t1-self.t0)
        self.scy=float(-h)/(v1-v0)
        self.bx = -self.scx*self.t0
        self.by = -self.scy*v1
        
    def draw(self, cr, ga, r, g, b):
    #def draw(self, cr):
        cr.set_source_rgb(r, g, b)
        cr.set_line_width(1.0)
        cr.save()
        matrix=cairo.Matrix(self.scx, 0, 0, self.scy, self.bx, self.by)
        cr.transform(matrix)
        start=False
        for v in ga:
            if v[0]>=self.t0 and start==False:
                start=True
                cr.move_to(v[0], v[1])
                continue
            if start: cr.line_to(v[0], v[1])
        cr.restore()
        cr.stroke()


    def inc_period(self):
        if self.truler._tperiod<ONE_DAY:
            self.truler.type+=1
            self.truler.tsetup()
            self.truler.t1=self.truler.t1
            self.darea.queue_draw()

    def dec_period(self):
        if self.truler._tperiod>TEN_MIN:
            self.truler.type-=1
            self.truler.tsetup()
            self.truler.t1=self.truler.t1
            self.darea.queue_draw()

    def second_ga(self, ga1, t01):
        dt=t01-self.t0
        self.ga1=[]
        for g in ga1:
            self.ga1.append((g[0]-dt, g[1]))
        self.darea.queue_draw()
    
################################################################################

if __name__ == "__main__":
    win = gtk.Window()
    win.connect('destroy', gtk.main_quit)
    ts=time.strptime("17.09.12 10:00:00", "%d.%m.%y %H:%M:%S")
    t0=time.mktime(ts)
    t1=t0+_4HOUR
    garea = GArea(_tstart=t0, _tperiod=FOUR_HOUR, _vunit='Volt')
    win.add(garea)
    win.show_all()

    gtk.main()

