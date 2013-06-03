#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       prmobj.py
#
#       Copyright 2012 New Systems Telecom, 2012
#       Developer: Alexander Gornak <ag@nstel.ru>
#
#
#
import time
import mysqldb
from prmc import *
################################################################################
SQL_DB=mysqldb.MySQLThread(DB_IP)

class Mes:
    def __init__(self, _time, _rpid, _vid, _value):
        self.t, self.rp_id, self.v_id, self.value = \
                _time, _rpid, _vid, _value

    def __str__(self):
        s=time.strftime("%H:%M:%S", time.localtime(self.t)) + ", %d, %d, %.2f" % (self.rp_id, self.v_id, self.value)
        return(s)

class RegPoint(object):
    def __init__(self, _id, _name, _desc, _caddr, _status):
        self.id, self.name, self.desc, self.c_addr, self._status = \
                 _id, _name, _desc, _caddr, _status
        self.A, self.kt, self.kn, self.kc, self.Ci=1250, 1, 1, 2, 1
        self.c_pass=''
        self.mon_data=dict()
        self.iter=None
        self.chiters=dict()

    def add_mon_data(self, mes):
        if self.id == mes.rp_id:
            self.mon_data[mes.v_id].append((mes.t, mes.value))
            SQL_DB.execute(SQL_INSERT_REG_DATA, (mes.t, mes.rp_id, mes.v_id, mes.value))

    def _get_status(self):
        return self._status

    def _set_status(self, value):
        if self._status!=value:
            self._status=value
            SQL_DB.execute(SQL_UPDATE_RP_STATUS, (self._status, self.id))

    status=property(_get_status, _set_status)

    def __str__(self):
        s="%d, " % self.id + self.name.encode('cp1251') +", %d" % (self.c_addr, )
        return(s)

class RegValue(object):
    def __init__(self, _id, _vname, _vshortname, _vunit, _vmon, _vmcmd_id, _v_acc):
        self.id, self.name, self.short_name, self.unit, self._mon, self.mcmd_id, self.acc = \
                 _id, _vname, _vshortname, _vunit, _vmon, _vmcmd_id, _v_acc

    def _get_mon(self):
        return self._mon
    def _set_mon(self, value):
        if self._mon!=value:
            self._mon=value
            SQL_DB.execute(SQL_UPDATE_V_MON, (self._mon, self.id))
    mon=property(_get_mon, _set_mon)

    def __str__(self):
        s="%d, " % self.id + self.name.encode('cp1251')
        return(s)

class RegPointList(list):
    def __init__(self):
        super(RegPointList, self).__init__()
    #def load_from_db(self):
        for row in SQL_DB.select(SQL_SEL_REG_POINTS):
            self.append(RegPoint(row['rp_id'], row['rp_name'], \
                        row['rp_desc'], row['c_addr'], row['rp_status']))
        for row in SQL_DB.select(SQL_SEL_COUNTERS):
            for rp in self:
                if rp.c_addr==row['c_addr']:
                    rp.A, rp.kt, rp.kn = row['c_A'], row['c_kt'], row['c_kn']
                    rp.c_pass=row['c_pass'].encode('cp1251')
                    break
    def get_rp_by_id(self, id):
        for rp in self:
            if rp.id==id: return rp
        return None


class RegValueList(list):
    def __init__(self):
        super(RegValueList, self).__init__()
    #def load_from_db(self):
        for row in SQL_DB.select(SQL_SEL_REG_VALUES):
            self.append(RegValue(row['v_id'], row['v_name'], row['v_short_name'], \
                                 row['v_unit'], row['v_mon'], row['v_mcmd_id'], row['v_acc']))

    def get_rv_by_id(self, id):
        for rv in self:
            if rv.id==id: return rv
        return None


if __name__ == "__main__":
    rpl=RegPointList()
    rvl=RegValueList()
    for rp in rpl:
        print rp
    for rv in rvl:
        print rv
    SQL_DB.close()

