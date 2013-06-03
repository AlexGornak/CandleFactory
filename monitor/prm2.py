#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       prm.py
#       prm - power registration monitor
#       Copyright 2012 New Systems Telecom, 2012
#       Developer: Alexander Gornak <ag@nstel.ru>
#
#
#
import sys
sys.path.append("../lib")

__version__ = '1.4'
#standart libs
import time
import math
import socket
import threading
import Queue
from struct import pack, unpack
import pygtk
pygtk.require('2.0')
import gtk
import gobject
import cairo
#my libs
#import sqldb
import crc16
#import msg
import garea
from prmc import *
import prmobj
import controller
################################################################################
class GArray(list):
    def __init__(self, _size):
        super(GArray, self).__init__()
        self.vmin=None
        self.vmax=None
        self.size=_size
    def append(self, entry):
        if type(entry) is tuple:
            if len(entry)==2:
                super(GArray, self).append(entry)
                if len(self)>self.size: self.pop(0)
                if self.vmin is None: self.vmin=entry[1]
                elif self.vmin>entry[1]: self.vmin=entry[1]
                if self.vmax is None: self.vmax=entry[1]
                elif self.vmax<entry[1]: self.vmax=entry[1]

STATUS_STR=['Выкл.', 'Вкл.']
################################################################################
################################################################################
MON_PERIOD_sec = 60
#GUI
class MyGui(gobject.GObject):
    def __init__(self):
        self.__gobject_init__()
        self.qres=Queue.Queue() #create queue for getting monitoring data
        self.CCtrl=controller.Controller()
        self.CCtrl.start()    #start modbus-like protocol as thread

        self.gui=gtk.Builder()
        self.gui.add_from_file("gui_prm.glade")
        dic={
             "on_window1_destroy":self.quit,
             "on_toolbutton1_clicked":self.quit,
             "on_toolbutton2_clicked":self.set_config,
             "on_toolbutton3_clicked":self.start_monitoring,
             "on_toolbutton4_clicked":self.stop_monitoring,
             "on_toolbutton7_clicked":self.new_graphic,
             "on_toolbutton5_clicked":self.zoom_in,
             "on_toolbutton6_clicked":self.zoom_out,
             }
        self.gui.connect_signals(dic)

        self.nb=self.gui.get_object("notebook1")

        self.tv=self.gui.get_object("treeview1")
        self.ts=self.gui.get_object("treestore1")
        self.tvcol=self.gui.get_object("treeviewcolumn1")
        lb=gtk.Label()
        lb.set_markup('<big><b>Статистика</b></big>')
        self.tvcol.set_widget(lb)
        lb.show()
        self.tv.append_column(self.tvcol)
        self.cell = gtk.CellRendererText()
        self.tvcol.pack_start(self.cell, True)
        self.tvcol.add_attribute(self.cell, 'markup', 0)
        self.tv.set_search_column(0)

        self.dialog2=self.gui.get_object("dialog2")
        self.dialog3=self.gui.get_object("dialog3")
        self.dialog4=self.gui.get_object("dialog4")
        self.msg_dialog=self.gui.get_object("messagedialog1")

        self.rp_top_it=self.ts.append(None, ['<b>Точки учета</b>'])
        self.win=self.gui.get_object("window1")
        self.pb1=self.gui.get_object("progressbar2")
        self.win.show_all()

        self.reg_values=prmobj.RegValueList()
        #self.reg_values.load_from_db()
        self.reg_points=prmobj.RegPointList()
        #self.reg_points.load_from_db()
        for rp in self.reg_points:
            for rv in self.reg_values:
                rp.mon_data[rv.id]=GArray(24*60*6)

        self.update_all_mon_addrs()
        self.update_all_mon_cmds()

        self.cb3=self.gui.get_object("combobox3")
        cell3 = gtk.CellRendererText()
        self.cb3.pack_start(cell3, True)
        self.cb3.add_attribute(cell3, 'text', 0)
        self.cb3model=self.cb3.get_model()

        self.cb4=self.gui.get_object("combobox4")
        cell4 = gtk.CellRendererText()
        self.cb4.pack_start(cell4, True)
        self.cb4.add_attribute(cell4, 'markup', 0)
        self.cb4model=self.cb4.get_model()

        for rp in self.reg_points:
            rp.iter=self.ts.append(self.rp_top_it, ['%s' % rp.name])
            s="Статус: "+STATUS_STR[rp.status]
            rp.chiters['Status']=self.ts.append(rp.iter, [s])

        rp_view=self.gui.get_object("treeview2")
        self.rp_store=self.gui.get_object("liststore5")
        cellr0=gtk.CellRendererText()
        cellr1=gtk.CellRendererToggle()
        cellr1.set_property('activatable', True)
        cellr1.connect('toggled', self.col1_toggled_cb, self.rp_store)
        col0=gtk.TreeViewColumn(None, cellr0, text=0)
        col0.set_property("expand", True)
        col1=gtk.TreeViewColumn(None, cellr1, active=1)
        rp_view.append_column(col0)
        rp_view.append_column(col1)

        rv_view=self.gui.get_object("treeview3")
        self.rv_store=self.gui.get_object("liststore6")
        for rv in self.reg_values:
            self.rv_store.append((rv.name+' ('+rv.short_name+')', rv.mon))
        cellr0=gtk.CellRendererText()
        cellr1=gtk.CellRendererToggle()
        cellr1.set_property('activatable', True)
        cellr1.connect('toggled', self.col1_toggled_cb, self.rv_store)
        col0=gtk.TreeViewColumn(None, cellr0, markup=0)
        col0.set_property("expand", True)
        col1=gtk.TreeViewColumn(None, cellr1, active=1)
        rv_view.append_column(col0)
        rv_view.append_column(col1)

        self.period_adj=self.gui.get_object("adjustment1")
        self.period_adj.set_value(MON_PERIOD_sec)

        self.src1=gobject.timeout_add(100, self.on_timer)
        self.src2=gobject.timeout_add(2500, self.on_timer2)

        self.monitoring_on=False
        self.monitoring_last_time=0
        #self.test_channel()
        for rp in self.reg_points:
            self.rp_store.append((rp.name, rp.status))


    def col1_toggled_cb( self, cell, path, model ):
        model[path][1] = not model[path][1]

    def message(self):
        self.msg_dialog.run()
        self.msg_dialog.hide()

    def get_rv_by_id(self, vid):
        for rv in self.reg_values:
            if rv.id==vid: return(rv)
        else: return(None)

    def get_rp_by_addr(self, addr):
        for rp in self.reg_points:
            if rp.c_addr==addr: return(rp)
        else: return(None)

    def update_mon_addr(self, rp):
        if rp.status:
            self.CCtrl.add_maddr(rp.c_addr)
        else:
            self.CCtrl.remove_maddr(rp.c_addr)

    def update_all_mon_addrs(self):
        for rp in self.reg_points:
            self.update_mon_addr(rp)

    def update_mon_cmd(self, mcmd_id):
        flag=0
        for rv in self.reg_values:
            if rv.mcmd_id==mcmd_id and rv.mon: flag=1
        self.CCtrl.set_mflag(mcmd_id, flag)

    def update_all_mon_cmds(self):
        self.CCtrl.clear_all_mflags()
        for rv in self.reg_values:
            if rv.mon: self.CCtrl.set_mflag(rv.mcmd_id, 1)

    def test_channel(self):
        self.dialog2.show()
        num_rp=len(self.reg_points)
        pos=0.0
        self.pb1.set_fraction(pos)
        for rp in self.reg_points:
            while gtk.events_pending():
                gtk.main_iteration()
            if rp.status:
                res=self.CCtrl.test_channel(rp.c_addr)
                #self.set_channel_status(rp.c_addr, res)
                pos+=1.0/float(num_rp)
                self.pb1.set_fraction(pos)
                print res, rp.c_addr
        self.dialog2.hide()

    def mark_mon_rqsts(self):
        for rqst in msg.rqsts_rtu:
            rqst.mon=0
            for vid in rqst.vids:
                if self.rv_mon[vid]:
                    rqst.mon=1
                    break

    def get_rv(self, vid):
        for rv in self.reg_values:
            if rv.id == vid: return(rv)
        return(None)

    def set_rv_list(self):
        self.cb4model.clear()
        for rv in self.reg_values:
            if rv.mon:
               self.cb4.append_text(rv.name+' ('+rv.short_name+')')
        self.cb4.set_active(0)

    def get_rv_index(self, rv_list_index):
        rvi=0
        li=0
        for rv in self.reg_values:
            if rv.mon:
                if rv_list_index==li:
                    break
                li+=1
            rvi+=1
        return(rvi)

    def set_rp_list(self):
        self.cb3model.clear()
        for rp in self.reg_points:
            if rp.status:
                self.cb3.append_text(rp.name)
        self.cb3.set_active(0)

    def get_rp_index(self, rp_list_index):
        rpi=0
        li=0
        for rp in self.reg_points:
            if rp.status:
                if rp_list_index==li:
                    break
                li+=1
            rpi+=1
        return (rpi)


    def update_treestore(self, rp, mes):
        for rv in self.reg_values:
            if rv.id==mes.v_id:
                s=rv.short_name
                break
        s+="=%.2f" % mes.value
        if mes.v_id in rp.chiters.keys():
            self.ts.set_value(rp.chiters[mes.v_id], 0, s)
        else:
            rp.chiters[mes.v_id]=self.ts.append(rp.iter, [s])

    def start_monitoring(self, widget):
        self.monitoring_last_time=time.time()
        self.CCtrl.run_monitoring(self.qres)
        self.monitoring_on=True

    def stop_monitoring(self, widget):
        self.monitoring_on=False

    def set_config(self, widget):
        global MON_PERIOD_sec
        if self.dialog4.run()==1:
            for rp, row in zip(self.reg_points, self.rp_store):
                if int(row[1])!=rp.status:
                    rp.status=int(row[1])
                    self.update_mon_addr(rp)
                    s="Статус: "+STATUS_STR[rp.status]
                    self.ts.set_value(rp.chiters['Status'], 0, s)
            for rv, row in zip(self.reg_values, self.rv_store):
                if int(row[1])!=rv.mon:
                    rv.mon=int(row[1])
                    self.update_mon_cmd(rv.mcmd_id)
            MON_PERIOD_sec=self.period_adj.get_value()
        else:
            for rp, row in zip(self.reg_points, self.rp_store):
                row[1]=bool(rp.status)
            for rv, row in zip(self.reg_values, self.rv_store):
                row[1]=bool(rv.mon)
        self.dialog4.hide()

    def on_timer(self):
        if self.monitoring_on \
        and time.time()-self.monitoring_last_time>=MON_PERIOD_sec \
        and self.CCtrl.q0.empty():
            self.monitoring_last_time=time.time()
            self.CCtrl.run_monitoring(self.qres)
        while 1:
            try:
                (res, rid, d)=self.qres.get(False)
            except:
                break
            else:
                if res==0:
                    s = "Нет ответа на запрос %d от %d" % (rid, ord(d[0]))
                    print s.decode('utf8')
                    return True
                if rid==OPEN_CH:
                    print "**************************"
                else:
                    if len(d)>4:
                        rp, mes_list=self.handle_mon_data(rid, d)
                        for m in mes_list:
                            rv=self.get_rv_by_id(m.v_id)
                            if rv.mon:
                                rp.add_mon_data(m)
                                self.update_treestore(rp, m)
                                print m
                        print "---------"
        return(True)

    def num4(self, dd):
        return((dd[0]<<24)+(dd[1]<<16)+(dd[2]<<8)+dd[3])
    def num3(self, dd):
        return(((dd[0] & 0x3f)<<16)+(dd[1]<<8)+dd[2])

    def handle_mon_data(self, req_id, d):
        rp=self.get_rp_by_addr(d[0])
        t=time.time()
        m=[]
        if req_id==FULL_ENERGY:
            if len(d)<17: return(rp, m)
            N=self.num4(d[1:5])
            Ap=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 1, Ap))
            N=self.num4(d[5:9])
            Am=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 2, Am))
            N=self.num4(d[9:13])
            Rp=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 3, Rp))
            N=self.num4(d[13:17])
            Rm=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 4, Rm))
        elif req_id==ACT_POWER_PH1:
            N=self.num3(d[1:4])
            P=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 5, P))
        elif req_id==ACT_POWER_PH2:
            N=self.num3(d[1:4])
            P=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 6, P))
        elif req_id==ACT_POWER_PH3:
            N=self.num3(d[1:4])
            P=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 7, P))
        elif req_id==ACT_POWER_SUM:
            N=self.num3(d[1:4])
            P=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 8, P))
        elif req_id==REACT_POWER_PH1:
            N=self.num3(d[1:4])
            Q=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 9, Q))
        elif req_id==REACT_POWER_PH2:
            N=self.num3(d[1:4])
            Q=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 10, Q))
        elif req_id==REACT_POWER_PH3:
            N=self.num3(d[1:4])
            Q=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 11, Q))
        elif req_id==REACT_POWER_SUM:
            N=self.num3(d[1:4])
            Q=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 12, Q))
        elif req_id==FULL_POWER_PH1:
            N=self.num3(d[1:4])
            S=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 13, S))
        elif req_id==FULL_POWER_PH2:
            N=self.num3(d[1:4])
            S=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 14, S))
        elif req_id==FULL_POWER_PH3:
            N=self.num3(d[1:4])
            S=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 15, S))
        elif req_id==FULL_POWER_SUM:
            N=self.num3(d[1:4])
            S=float(N*rp.kt*rp.kn*rp.kc)/1000.0
            m.append(prmobj.Mes(t, rp.id, 16, S))
        elif req_id==U_PH1:
            N=self.num3(d[1:4])
            U=float(N*rp.kn)/100.0
            m.append(prmobj.Mes(t, rp.id, 17, U))
        elif req_id==U_PH2:
            N=self.num3(d[1:4])
            U=float(N*rp.kn)/100.0
            m.append(prmobj.Mes(t, rp.id, 18, U))
        elif req_id==U_PH3:
            N=self.num3(d[1:4])
            U=float(N*rp.kn)/100.0
            m.append(prmobj.Mes(t, rp.id, 19, U))
        elif req_id==I_PH1:
            N=self.num3(d[1:4])
            I=float(N*rp.kt*rp.Ci)/10.0
            m.append(prmobj.Mes(t, rp.id, 20, I))
        elif req_id==I_PH2:
            N=self.num3(d[1:4])
            I=float(N*rp.kt*rp.Ci)/10.0
            m.append(prmobj.Mes(t, rp.id, 21, I))
        elif req_id==I_PH3:
            N=self.num3(d[1:4])
            I=float(N*rp.kt*rp.Ci)/10.0
            m.append(prmobj.Mes(t, rp.id, 22, I))
        elif req_id==FULL_ENERGY_W_LOSS:
            if len(d)<17: return(m)
            N=self.num4(d[1:5])
            Ap=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 23, Ap))
            N=self.num4(d[5:9])
            Am=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 24, Am))
            N=self.num4(d[9:13])
            Rp=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 25, Rp))
            N=self.num4(d[13:17])
            Rm=float(N*rp.kt*rp.kn)/(2*rp.A)
            m.append(prmobj.Mes(t, rp.id, 26, Rm))
        elif req_id==COS_PH1:
            N=self.num3(d[1:4])
            Cos=float(N)/100.0
            m.append(prmobj.Mes(t, rp.id, 27, Cos))
        elif req_id==COS_PH2:
            N=self.num3(d[1:4])
            Cos=float(N)/100.0
            m.append(prmobj.Mes(t, rp.id, 28, Cos))
        elif req_id==COS_PH3:
            N=self.num3(d[1:4])
            Cos=float(N)/100.0
            m.append(prmobj.Mes(t, rp.id, 29, Cos))
        elif req_id==COS_SUM:
            N=self.num3(d[1:4])
            Cos=float(N)/100.0
            m.append(prmobj.Mes(t, rp.id, 30, Cos))
        elif req_id==U_BPH12:
            N=self.num3(d[1:4])
            U=float(N*rp.kn)/100.0
            m.append(prmobj.Mes(t, rp.id, 31, U))
        elif req_id==U_BPH23:
            N=self.num3(d[1:4])
            U=float(N*rp.kn)/100.0
            m.append(prmobj.Mes(t, rp.id, 32, U))
        elif req_id==U_BPH31:
            N=self.num3(d[1:4])
            U=float(N*rp.kn)/100.0
            m.append(prmobj.Mes(t, rp.id, 33, U))
        elif req_id==F_HZ:
            N=self.num3(d[1:4])
            F=float(N)/100.0
            m.append(prmobj.Mes(t, rp.id, 34, F))
        return(rp, m)

    def on_timer2(self):
        if self.monitoring_on:
            pn=self.nb.get_current_page()
            if pn!=-1:
                darea=self.nb.get_nth_page(pn)
                ll=len(darea.ga)
                if ll:
                    t1=darea.ga[ll-1][0]
                    darea.truler.t1=t1
                    darea.queue_draw()
        return True

    def add_tab(self, rpi, rvi):
        rp=self.reg_points[rpi]
        rv=self.reg_values[rvi]
        if len(rp.mon_data[rv.id])==0:
            self.message()
            return
        hbox=gtk.HBox(False, 0)
        label=gtk.Label()
        label.set_markup(rp.name+': '+rv.short_name)
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

        widget=garea.GArea(_ga=rp.mon_data[rv.id], _vunit=rv.unit, _tperiod=garea._10MIN)

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
        self.set_rp_list()
        self.set_rv_list()
        rpli, rvli = -1, -1
        if self.dialog3.run()==1:
            rpli=self.cb3.get_active()
            rvli=self.cb4.get_active()
        self.dialog3.hide()
        if rpli!=-1 and rvli!=-1:
            rpi=self.get_rp_index(rpli)
            rvi=self.get_rv_index(rvli)
            self.add_tab(rpi, rvi)

    def zoom_in(self, widget):
        pn=self.nb.get_current_page()
        if pn!=-1:
            dr_area=self.nb.get_nth_page(pn)
            dr_area.inc_period()

    def zoom_out(self, widget):
        pn=self.nb.get_current_page()
        if pn!=-1:
            dr_area=self.nb.get_nth_page(pn)
            dr_area.dec_period()

    def quit(self, widget):
        prmobj.SQL_DB.close()
        self.CCtrl.close()
        gobject.source_remove(self.src1)
        gobject.source_remove(self.src2)
        self.win.destroy()
        gtk.main_quit()

################################################################################

if __name__ == "__main__":
    App=MyGui()
    gtk.main()

