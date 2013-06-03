#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       controller.py
#
#       Copyright 2012 New Systems Telecom, 2012
#       Developer: Alexander Gornak <ag@nstel.ru>
#
#
#

import time
import socket
import threading
import Queue
import crc16
from struct import pack, unpack
import prmc
################################################################################
################################################################################
#Protocol states
STATE_IDLE = 0
STATE_SEND_DATA = 1
STATE_WAIT_DATA = 2

MADDR = prmc.MasterAddr
SADDR = prmc.SlaveAddr

def to_2_10(a):
    b0=a%10
    b1=(a//10)%10
    return (b1*16+b0)

################################################################################
class Controller(threading.Thread):
    MAX_RETRY = 1
    TIME_OUT = 1.0
    def __init__(self):
        super(Controller, self).__init__()
        self.q0=Queue.Queue()   #low priority queue for monitoring
        self.q1=Queue.Queue()   #high priority queue
        self.__q=Queue.Queue()   #output queue for executing commands
        self.__maddrs=[]         #list of addresses for monitoring
        self.__mflags={}
        for mc in prmc.mcmds:
            self.__mflags[mc[0]]=0
        self.daemon=True
        #self.start()

    def run(self):
        sock=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(MADDR)
        sock.settimeout(self.TIME_OUT)
        state=STATE_IDLE
        slave_id=0
        retry=0
        while True:
            if state==STATE_IDLE:
                try:
                    rid, req, delay, qres = self.q1.get(False)
                except:
                    try:
                        rid, req, delay, qres = self.q0.get(False)
                    except:
                        pass
                    else:
                        state=STATE_SEND_DATA
                else:
                    state=STATE_SEND_DATA
                if state==STATE_SEND_DATA:
                    if req=='--close--': break
                    if delay>0.0: time.sleep(delay)
                    retry=0
            if state==STATE_SEND_DATA:
                slave_id=req[0]
                sock.sendto(req, SADDR)
                retry+=1
                state=STATE_WAIT_DATA
            if state==STATE_WAIT_DATA:
                try:
                    data, addr = sock.recvfrom(512)
                except:
                    if retry < self.MAX_RETRY:
                        state=STATE_SEND_DATA
                    else:
                        qres.put((0, rid, req))
                        state=STATE_IDLE
                else:
                    crc=crc16.calcString(data, crc16.INITIAL_MODBUS)
                    if (crc==0):
                        d=map(ord, data)
                        if len(d)==4 and (d[1] & 0x0f)==0x06:
                            state=STATE_SEND_DATA
                            retry-=1
                        else:
                            qres.put((1, rid, d))
                            state=STATE_IDLE
                    else:
                        qres.put((0, rid, req))
                        state=STATE_IDLE
        sock.close()

    def make_req(self, addr, cmd):
    # make request: add address and CRC to the command binary string
    # addr - counter's address (0 - 0xef, 0xfe)
    # cmd - command binary string
    # return: request binary string
        req=pack("=B", addr)+cmd
        crc=crc16.calcString(req, crc16.INITIAL_MODBUS)
        req+=pack("=H", crc)
        return req

    def send(self, rid, req, delay, priority, qres):
    # send request in controller queue
    # rid - request id
    # req - request binary string with address and CRC
    # delay - delay in seconds befor request send
    # priority - if = 1 send via high priority queue
    #            else (= 0) send via low priority queue
    # qres - queue for results output
        if priority==1: q=self.q1
        else: q=self.q0
        q.put((rid, req, delay, qres))

    def exec_cmd(self, addr, cmd_key, params=None):
        cmd=prmc.cmds[cmd_key]
        if type(params)==int:
            cmd+=pack("=B", params)
        elif type(params)==str:
            cmd+=params
        elif type(params)==tuple:
            for p in params:
                cmd+=pack("=B", p)
        req=self.make_req(addr, cmd)
        self.send(cmd_key, req, 0.0, 1, self.__q)
        return(self.__q.get())

    def send_mcmd(self, addr, mc, qres):
        req=self.make_req(addr, prmc.cmds[mc[0]])
        self.send(mc[0], req, mc[1], 0, qres)

    def run_monitoring(self, qres):
        for addr in self.__maddrs:
            opn_req=self.make_req(addr, prmc.cmds[prmc.OPEN_CH]+'000000')
            self.send(prmc.OPEN_CH, opn_req, 0.0, 0, qres)
            for mc in prmc.mcmds:
                if self.__mflags[mc[0]]:
                    self.send_mcmd(addr, mc, qres)

    def close(self):
        self.q0.put((0, '--close--', 0.0, None))

    def test_channel(self, addr):
        res, rid, d = self.exec_cmd(addr, prmc.TEST_CH)
        if res and d[1]&0x0f==0: return True
        else: return False

    def test_channel_via_reader(self, mac_str):
    # mac_str - binary string of reader in big endian notation (first byte is more significant)
    # return: address of counter connected to the reader or zero
        req="\xf1"+mac_str
        key=prmc.TEST_CH
        req1=self.make_req(0x00, prmc.cmds[key])
        req+=req1
        self.send(key, req, 0.0, 1, self.__q)
        res, rid, d = self.__q.get()
        if res and d[1]&0x0f==0: return(d[0])
        else: return(0)

    def open_channel(self, addr, password):
        res, rid, d = self.exec_cmd(addr, prmc.OPEN_CH, password)
        if res and d[1]&0x0f==0: return True
        else: return False

    def close_channel(self, addr):
        res, rid, d = self.exec_cmd(addr, prmc.CLOSE_CH)
        return(res)

    def set_addr(self, old_addr, new_addr):
        res, rid, d = self.exec_cmd(old_addr, prmc.SET_ADDR, new_addr)
        if res and d[1]==0: return True
        else: return False

    def set_time(self, addr, s, m, h, wd, dd, mm, yy, winter):
        tt=(to_2_10(s), to_2_10(m), to_2_10(h), to_2_10(wd), \
            to_2_10(dd), to_2_10(mm), to_2_10(yy), to_2_10(winter))
        res, rid, d = self.exec_cmd(addr, prmc.SET_TIME, tt)
        if res and d[1]==0: return True
        else: return False

    def set_local_time(self, addr):
        ts=time.localtime()
        res=self.set_time(addr, ts.tm_sec, ts.tm_min, ts.tm_hour, ts.tm_wday+1, \
                          ts.tm_mday, ts.tm_mon, ts.tm_year % 100, 0)
        return(res)

    def correct_time(self, addr, corr_sec):
        res, rid, d = self.exec_cmd(addr, prmc.CORRECT_TIME, pack(">h", corr_sec))
        if res:
            if d[1]==1: return False
            else: return True
        else: return False

    def set_power_acc_time(self, addr, acctime):
    # addr - countre's address
    # acctime - power accumulation time in minutes (1, 2, 3, 4, 5, 6, 10, 12, 15, 20, 30)
        res, rid, d = self.exec_cmd(addr, prmc.POWER_ACC_TIME, acctime)
        if res and d[1]==0: return True
        else: return False

    def reset_energy_regs(self, addr):
        res, rid, d = self.exec_cmd(addr, prmc.RESET_ENERGY_REGS)
        if res and (d[1]&0x0f)==0:
            dd=d[1]>>4
            if dd: time.sleep(dd)
            return True
        else: return False

    def get_kt(self, addr):
        res, rid, d = self.exec_cmd(addr, prmc.GET_KT)
        if res and len(d)>=5:
            kn=(d[1]<<8)+d[2]
            kt=(d[3]<<8)+d[4]
            return ((kn, kt))
        else:
            return ((1, 1))

    def add_maddr(self, maddr):
        if maddr not in self.__maddrs:
            self.__maddrs.append(maddr)

    def remove_maddr(self, maddr):
        if maddr in self.__maddrs:
            self.__maddrs.remove(maddr)

    def set_mflag(self, mcmd_id, flag):
        self.__mflags[mcmd_id]=flag
        #print mcmd_id, self.__mflags[mcmd_id]

    def clear_all_mflags(self):
        for k in self.__mflags.keys():
            self.__mflags[k]=0


################################################################################
if __name__ == "__main__":
    ctrl=Controller()
    ctrl.start()
    #ctrl.test_channel(20)
    if ctrl.open_channel(10, "000000"):
        print "ok"
        #print mb.correct_time(20, 60)
    #ctrl.set_mon_flag("energy", 1)
    #print ctrl.get_mon_flag("energy")
    ctrl.close()

