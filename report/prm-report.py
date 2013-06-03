#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       prm-report.py
#       
#       Copyright 2012 New Systems Telecom, 2012
#       Developer: Alexander Gornak <ag@nstel.ru>
#
#
#
import sys
sys.path.append("../lib")

__version__ = '1.0'
import time
import math
#import locale
import Queue
import pygtk
pygtk.require('2.0')
import gtk
import gobject
#import sqldb
import crc16
from struct import pack, unpack
import cairo
import garea
from prmc import *
import prmobj
import gdate
import xlwt
from datetime import datetime
################################################################################
def get_time(YYYY, MM, DD, hh, mm):
    ts=(YYYY, MM, DD, hh, mm, 0, 0, 0, 0)
    return(time.mktime(ts))

class SmoothFunc:
    def __init__(self, ga, interval_min):
        N1=len(ga)
        a=float(ga[0][0])
        b=float(ga[N1-1][0])
        M=int(math.floor((b-a)/(interval_min*60)+0.5))
        K=int(N1/M)+1
        ff=[]
        j=0
        for i in range(M*K+1):
            t=a+(b-a)*i/(M*K)
            while (j<N1-2) and (t>=ga[j+1][0]): j+=1
            t1=ga[j+1][0]
            t0=ga[j][0]
            f1=ga[j+1][1]
            f0=ga[j][1]
            ff.append((f1-f0)*(t-t0)/(t1-t0)+f0)
        #for f in ff: print f
        A=float((K-1)*(K+1))/(6*K)
        B=float(2*K**2+1)/(3*K)
        C=float((K+1)*(2*K+1))/(6*K)
        D=[]
        D.append(0.0)
        for l in range(K):
            D[0]+=(1.0-float(l)/K)*ff[l]
        for m in range(1, M):
            D.append(0.0)
            for l in range(K):
                D[m]+=float(l)*ff[(m-1)*K+l]/K+(1.0-float(l)/K)*ff[m*K+l]
        D.append(0.0)
        for l in range(1, K+1):
            D[M]+=float(l)*ff[(M-1)*K+l]/K
        aa=[]
        bb=[]
        aa.append(-A/C)
        bb.append(D[0]/C)
        for m in range(1, M):
            aa.append(-A/(A*aa[m-1]+B))
            bb.append((D[m]-A*bb[m-1])/(A*aa[m-1]+B))
        self.F=[(0.0, 0.0)]*(M+1)
        self.F[M]=(b,(D[M]-A*bb[M-1])/(A*aa[M-1]+C))
        for m in range(M, 0, -1):
            self.F[m-1]=(a+(b-a)*(m-1)/M, aa[m-1]*self.F[m][1]+bb[m-1])
        #print '*********'
        #for t, f in self.F:
            #print t, f
        #'''

def extract_data(g, T0, T1, dT):
    data=[]
    N=len(g)
    if N==0: return data
    while T0+dT<=g[0][0]:
        data.append([None, None])
        T0+=dT
    data.append([g[0][1], None])
    T0+=dT
    k=0
    while k<N-1:
        while T0<g[k+1][0]:
            v=(g[k+1][1]-g[k][1])*(T0-g[k][0])/(g[k+1][0]-g[k][0])+g[k][1]
            data.append([v,None])
            T0+=dT
        k+=1
    data.append([g[k][1], None])
    T0+=dT
    while T0<=T1:
        data.append([None, None])
        T0+=dT
    N = len(data)
    i=0
    while (i<N) and (data[i][0] is None):
		i+=1
    if i<N:
		while (i<N-1) and (data[i+1][0] is not None):
			data[i+1][1]=data[i+1][0]-data[i][0]
			i+=1
    return data

################################################################################
TIME_INTERVALS = [
                  ("1 сутки", ONE_DAY),
                  ("1 неделя", ONE_WEEK),
                  ("1 месяц", ONE_MONTH),
                  ("1 год", ONE_YEAR)
                  ]
TIME_STEPS = [
                  ("1 минута", ONE_MIN),
                  ("30 минут", THIRTY_MIN),
                  ("1 сутки", ONE_DAY)
                  ]
TSTEP = 300.0
#GUI
class MyGui(gobject.GObject):
    def __init__(self):
        self.gui=gtk.Builder()
        self.gui.add_from_file("gui_rep.glade")
        self.win=self.gui.get_object("mainwindow")
        #self.vbox=self.gui.get_object("vbox1")
        self.nb=self.gui.get_object("notebook1")
        self.cb1=self.gui.get_object("combobox1")
        self.cb2=self.gui.get_object("combobox2")
        self.cb3=self.gui.get_object("combobox3")
        self.msgbox1=self.gui.get_object("msgbox1")
        self.dialog1=self.gui.get_object("dialog1")
        table1=self.gui.get_object("table1")
        self.gdate=gdate.GDate()
        table1.attach(self.gdate, 1, 2, 1, 2, yoptions=0, xpadding=12)
        self.cb1.connect("changed", self.cb1_changed, self.gdate)

        self.filechooser=self.gui.get_object("filechooserwidget1")
        self.cb4=self.gui.get_object("combobox4")
        self.cb5=self.gui.get_object("combobox5")
        filefilter1=self.gui.get_object("filefilter1")
        filefilter1.add_pattern("*.xls")
        self.dialog3=self.gui.get_object("dialog3")
        self.gdate1=gdate.GDate()
        table2=self.gui.get_object("table2")
        table2.attach(self.gdate1, 1, 2, 1, 2, yoptions=0, xpadding=12)
        self.cb4.connect("changed", self.cb4_changed, self.gdate1)

        self.rpl=prmobj.RegPointList()
        self.rvl=prmobj.RegValueList()
        #for rv in self.rvl: print rv

        render=gtk.CellRendererText()
        self.cb1.pack_start(render, True)
        self.cb4.pack_start(render, True)
        self.cb5.pack_start(render, True)
        self.cb1.add_attribute(render, 'text', 0)
        self.cb4.add_attribute(render, 'text', 0)
        self.cb5.add_attribute(render, 'text', 0)
        self.cb5model=self.cb5.get_model()
        for ti in TIME_INTERVALS:
            self.cb1.append_text(ti[0])
            self.cb4.append_text(ti[0])
        self.cb1.set_active(0)
        self.cb4.set_active(0)
        for ts in TIME_STEPS:
			self.cb5.append_text(ts[0])
        self.cb5.set_active(0)
        #self.cb1.set_property("sensitive", False)

        render=gtk.CellRendererText()
        self.cb2.pack_start(render, True)
        self.cb2.add_attribute(render, 'text', 0)
        for rp in self.rpl:
            self.cb2.append_text(rp.name+': '+rp.desc)
        self.cb2.set_active(0)

        render=gtk.CellRendererText()
        self.cb3.pack_start(render, True)
        self.cb3.add_attribute(render, 'markup', 0)
        for rv in self.rvl:
            self.cb3.append_text(rv.name+' ('+rv.short_name+')')
        self.cb3.set_active(0)
        
        self.dialog4=self.gui.get_object("dialog4")
        self.pb1=self.gui.get_object("progressbar1")

        dic={
             "on_mainwindow_destroy":self.quit,
             "on_toolbutton2_clicked":self.quit,
             "on_toolbutton1_clicked":self.new_graphic,
             "on_toolbutton3_clicked":self.graphic2,
             "on_toolbutton4_clicked":self.report1
             }
        self.gui.connect_signals(dic)
        self.win.show_all()

    def cb1_changed(self, widget, wgdate):
        i=widget.get_active()
        interval=TIME_INTERVALS[i][1]
        wgdate.set_interval(interval)

    def cb4_changed(self, widget, wgdate):
        i=widget.get_active()
        interval=TIME_INTERVALS[i][1]
        wgdate.set_interval(interval)
        self.cb5model.clear()
        start=0
        if (i>0) and (i<3):
            start=1
        elif i>=3:
            start=2
        for ts in TIME_STEPS[start:]:
            self.cb5.append_text(ts[0])
        self.cb5.set_active(0)

    def get_data_from_db(self, rpid, rvid, t0, t1):
        ga=[]
        v0, v1 = None, None
        for row in prmobj.SQL_DB.select(SQL_SEL_POWER_DATA, (rpid, rvid, t0, t1)):
            ga.append((row['time'], row['value']))
            if v0 is None:
                v0=row['value']
                v1=v0
            elif row['value']<v0: v0=row['value']
            elif row['value']>v1: v1=row['value']
        return ((ga, v0, v1))

    def get_data_from_db1(self, rpid, rvid, t0, t1):
        ga=[]
        v0, v1 = None, None
        for row in prmobj.SQL_DB.select(SQL_SEL_REG_DATA, (rpid, rvid, t0, t1)):
            ga.append((row['time'], row['value']))
            if v0 is None:
                v0=row['value']
                v1=v0
            elif row['value']<v0: v0=row['value']
            elif row['value']>v1: v1=row['value']
        return ((ga, v0, v1))

    def add_tab(self, inti, rpi, rvi, tstart, tperiod):
        rp=self.rpl[rpi]
        rv=self.rvl[rvi]
        tend=tstart+tperiod
        ga, v0, v1 = self.get_data_from_db(rp.id, rv.id, tstart, tend)
        #ga=self.get_data_from_db2(rp.id, rv.id, tstart, tend, TSTEP)
        if len(ga)<2:
            self.msgbox1.run()
            self.msgbox1.hide()
            return

        hbox=gtk.HBox(False, 0)
        label=gtk.Label(rp.name)
        hbox.pack_start(label)

        close_image=gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_MENU)
        image_w, image_h = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)

        #make the close button
        btn = gtk.Button()
        btn.set_relief(gtk.RELIEF_NONE)
        btn.set_focus_on_click(False)
        btn.add(close_image)
        hbox.pack_start(btn, False, False)

        #this reduces the size of the button
        style = gtk.RcStyle()
        style.xthickness = 0
        style.ythickness = 0
        btn.modify_style(style)

        hbox.show_all()

        widget = garea.GArea(_ga=ga, _tstart=tstart, _tperiod=tperiod, _vunit=rv.unit)
        widget.set_ref_dict(inti, rpi, rvi)
        #add the tab
        self.nb.insert_page(widget, hbox)
        self.nb.show_all()
        #connect the close button
        btn.connect('clicked', self.on_closetab_button_clicked, widget)

    def on_closetab_button_clicked(self, sender, widget):
        #get the page number of the tab we wanted to close
        pagenum = self.nb.page_num(widget)
        #and close it
        self.nb.remove_page(pagenum)

    def new_graphic(self, widget):
        if self.dialog1.run()==1:
            i1=self.cb1.get_active()
            interval=TIME_INTERVALS[i1][1]
            self.t0=self.gdate.get_time()
            i2=self.cb2.get_active()
            i3=self.cb3.get_active()
            self.dialog1.hide()
            self.add_tab(i1, i2, i3, self.t0, interval)
        else: self.dialog1.hide()

    def graphic2(self, widget):
        pn=self.nb.get_current_page()
        if pn!=-1:
            gw=self.nb.get_nth_page(pn)
            i1, i3 = gw.ref['interval'], gw.ref['regvalue']
            self.cb1.set_active(i1)
            self.cb1.set_property('sensitive', False)
            self.cb3.set_active(i3)
            self.cb3.set_property('sensitive', False)
            tperiod=TIME_INTERVALS[i1][1]
            #self.gdate.set_interval(interval)
            if self.dialog1.run()==1:
                self.dialog1.hide()
                tstart=self.gdate.get_time()
                i2=self.cb2.get_active()
                rp=self.rpl[i2]
                rv=self.rvl[i3]
                tend=tstart+tperiod
                ga, v0, v1 = self.get_data_from_db(rp.id, rv.id, tstart, tend)
                if len(ga)>=2:
                    gw.second_ga(ga, tstart)
            else: self.dialog1.hide()
            self.cb1.set_property('sensitive', True)
            self.cb3.set_property('sensitive', True)


    def report1(self, widget):
        if self.dialog3.run()==1:
            self.dialog3.hide()
            fname=self.filechooser.get_filename()
            if fname is not None:
                self.dialog4.show()
                pos=0.0
                self.pb1.set_fraction(pos)
                rvids=[]
                for rv in self.rvl:
                    if rv.mon and rv.acc: rvids.append(rv.id)
                rpids=[]
                for rp in self.rpl:
                    #if rp.status:
                    rpids.append(rp.id)
                tstart=self.gdate1.get_time()
                i1=self.cb4.get_active()
                tend=tstart+TIME_INTERVALS[i1][1]
                start=0
                if (i1>0) and (i1<3): start=1
                elif (i1>=3): start=2
                i2=self.cb5.get_active()
                dt=TIME_STEPS[start+i2][1]
                sss="1 минуту"
                if dt==THIRTY_MIN: sss="30 минут"
                elif dt==ONE_DAY: sss="1 сутки"
                heads=['Дата']
                for rvid in rvids:
                    rv=self.rvl.get_rv_by_id(rvid)
                    heads.append(rv.name)
                    heads.append("Расход за"+sss)
                head_xf = xlwt.easyxf('font: bold on; align: wrap on, vert centre, horiz center')
                if start+i2==2:
                    date_xf = xlwt.easyxf(num_format_str='yyyy-mm-dd')
                    col_width = 3292
                else:
					date_xf = xlwt.easyxf(num_format_str='yyyy-mm-dd HH:MM')
					col_width = 4292
                value_xf = xlwt.easyxf(num_format_str='# ##0.00')

                wb=xlwt.Workbook(encoding='utf-8')
                pb_size=len(rpids)*(len(rvids)+1)
                for rpid in rpids:
                    rp=self.rpl.get_rp_by_id(rpid)
                    ws=wb.add_sheet(rp.name)
                    ws.col(0).width=col_width
                    for colx, val in enumerate(heads):
                        ws.write(0, colx, val, head_xf)
                    ws.set_panes_frozen(True)
                    ws.set_horz_split_pos(1)
                    ws.set_remove_splits(True)
                    rowx, colx = 1, 0
                    t=tstart
                    while t<=tend:
                        ws.write(rowx, colx, datetime.fromtimestamp(t), date_xf)
                        t+=dt
                        rowx+=1
                    colx+=1
                    pos+=1.0/pb_size
                    self.pb1.set_fraction(min(pos, 1.0))
                    for rvid in rvids:
                        g, v0, v1 = self.get_data_from_db1(rpid, rvid, tstart, tend)
                        rep=extract_data(g, tstart, tend, dt)
                        for rowx, val in enumerate(rep):
                            ws.write(rowx+1, colx, val[0], value_xf)
                            ws.write(rowx+1, colx+1, val[1], value_xf)
                        colx+=2
                        pos+=1.0/pb_size
                        self.pb1.set_fraction(min(pos, 1.0))
                        while gtk.events_pending():
							gtk.main_iteration()
                wb.save(fname)
                self.dialog4.hide()
        else:
			self.dialog3.hide()



    def quit(self, widget):
        prmobj.SQL_DB.close()
        self.win.destroy()
        gtk.main_quit()

################################################################################

if __name__ == "__main__":
    App=MyGui()
    gtk.main()

