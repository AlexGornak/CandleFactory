#!/usr/bin/env python
# -*- coding: UTF-8 -*-
#
#       prmc.py
#
#       Copyright 2012 New Systems Telecom, 2012
#       Developer: Alexander Gornak <ag@nstel.ru>
#
#
#
################################################################################
MasterAddr = ("172.23.11.94", 57580)
SlaveAddr = ("172.23.11.234", 57590)

DB_IP = '172.23.11.94'
SQL_SEL_REG_POINTS = 'SELECT * FROM reg_points'
SQL_SEL_REG_VALUES = 'SELECT * FROM reg_values'
SQL_SEL_COUNTERS = 'SELECT * FROM counters'
SQL_SEL_REG_DATA = 'SELECT time, value FROM registrations WHERE rp_id=%s AND v_id=%s AND time>=%s AND time<%s'
SQL_SEL_POWER_DATA = 'SELECT time, value FROM power_data WHERE rp_id=%s AND v_id=%s AND time>=%s AND time<%s'
SQL_UPDATE_RP_STATUS = 'UPDATE reg_points SET rp_status=%s WHERE  rp_id=%s'
SQL_UPDATE_V_MON = 'UPDATE reg_values SET v_mon=%s WHERE  v_id=%s'
SQL_INSERT_REG_DATA = 'INSERT INTO registrations(time, rp_id, v_id, value) VALUES(%s, %s, %s, %s)'

ONE_MIN = 60
TEN_MIN = 600
THIRTY_MIN = 1800
ONE_HOUR = 3600
FOUR_HOUR = 14400
TWENTY_HOUR = 43200
ONE_DAY = 86400
ONE_WEEK = 604800
ONE_MONTH = 2678400
ONE_YEAR = 31622400

##Counters commands
TEST_CH = 1
OPEN_CH = 2
CLOSE_CH = 3
SET_ADDR = 4
SET_TIME = 5
CORRECT_TIME = 6
POWER_ACC_TIME = 7
RESET_ENERGY_REGS = 8
GET_KT = 9
FULL_ENERGY = 10
ACT_POWER_PH1 = 11
ACT_POWER_PH2 = 12
ACT_POWER_PH3 = 13
ACT_POWER_SUM = 14
REACT_POWER_PH1 = 15
REACT_POWER_PH2 = 16
REACT_POWER_PH3 = 17
REACT_POWER_SUM = 18
FULL_POWER_PH1 = 19
FULL_POWER_PH2 = 20
FULL_POWER_PH3 = 21
FULL_POWER_SUM = 22
U_PH1 = 23
U_PH2 = 24
U_PH3 = 25
I_PH1 = 26
I_PH2 = 27
I_PH3 = 28
FULL_ENERGY_W_LOSS = 29
SET_KI = 30
COS_PH1 = 32
COS_PH2 = 33
COS_PH3 = 34
COS_SUM = 35
U_BPH12 = 36
U_BPH23 = 37
U_BPH31 = 38
F_HZ = 39

cmds =  {   TEST_CH: "\x00",
            OPEN_CH: "\x01",
            CLOSE_CH: "\x02",
            SET_ADDR: "\x03\x05",
            SET_TIME: "\x03\x0c",
            CORRECT_TIME: "\x03\x0b",
            POWER_ACC_TIME: "\x03\x00",
            RESET_ENERGY_REGS: "\x03\x20",
            GET_KT: "\x08\x02",
            FULL_ENERGY: "\x05\x00\x00",
            ACT_POWER_PH1: "\x08\x11\x01",
            ACT_POWER_PH2: "\x08\x11\x02",
            ACT_POWER_PH3: "\x08\x11\x03",
            ACT_POWER_SUM: "\x08\x11\x00",
            REACT_POWER_PH1: "\x08\x11\x05",
            REACT_POWER_PH2: "\x08\x11\x06",
            REACT_POWER_PH3: "\x08\x11\x07",
            REACT_POWER_SUM: "\x08\x11\x04",
            FULL_POWER_PH1: "\x08\x11\x09",
            FULL_POWER_PH2: "\x08\x11\x0a",
            FULL_POWER_PH3: "\x08\x11\x0b",
            FULL_POWER_SUM: "\x08\x11\x08",
            U_PH1: "\x08\x11\x11",
            U_PH2: "\x08\x11\x12",
            U_PH3: "\x08\x11\x13",
            I_PH1: "\x08\x11\x21",
            I_PH2: "\x08\x11\x22",
            I_PH3: "\x08\x11\x23",
            FULL_ENERGY_W_LOSS: "\x0a\x00\x00\x09\x0f\x00",
            SET_KI: "\x03\x1c",
            COS_PH1: "\x08\x11\x31",
            COS_PH2: "\x08\x11\x32",
            COS_PH3: "\x08\x11\x33",
            COS_SUM: "\x08\x11\x30",
            U_BPH12: "\x08\x11\x15",
            U_BPH23: "\x08\x11\x16",
            U_BPH31: "\x08\x11\x17",
            F_HZ: "\x08\x11\x40"
        }

mcmds = (   (FULL_ENERGY, 0.0),
            (ACT_POWER_PH1, 0.0),
            (ACT_POWER_PH2, 0.0),
            (ACT_POWER_PH3, 0.0),
            (ACT_POWER_SUM, 0.0),
            (REACT_POWER_PH1, 0.0),
            (REACT_POWER_PH2, 0.0),
            (REACT_POWER_PH3, 0.0),
            (REACT_POWER_SUM, 0.0),
            (FULL_POWER_PH1, 0.0),
            (FULL_POWER_PH2, 0.0),
            (FULL_POWER_PH3, 0.0),
            (FULL_POWER_SUM, 0.0),
            (U_PH1, 0.25),
            (U_PH2, 0.0),
            (U_PH3, 0.0),
            (I_PH1, 0.0),
            (I_PH2, 0.0),
            (I_PH3, 0.0),
            (FULL_ENERGY_W_LOSS, 0.0),
            (COS_PH1, 0.0),
            (COS_PH2, 0.0),
            (COS_PH3, 0.0),
            (COS_SUM, 0.0),
            (U_BPH12, 0.0),
            (U_BPH23, 0.0),
            (U_BPH31, 0.0),
            (F_HZ, 0.0)
        )
if __name__ == "__main__":
    pass

