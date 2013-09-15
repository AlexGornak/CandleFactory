#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       sqldb.py
#       
#       Copyright 2012 Alex <agornak@gmail.com>
#       
#              
#
import threading
import Queue
import MySQLdb as mdb

################################################################################
class MySQLThread(threading.Thread):
    def __init__(self, DB_Server_IP):
        super(MySQLThread, self).__init__()
        self.db_ip=DB_Server_IP
        self.reqs=Queue.Queue()
        self.start()
    def run(self):
        conn=mdb.connect(self.db_ip, 'root', 'agroot', 'prm', use_unicode=True, charset='utf8')
        cursor=conn.cursor(mdb.cursors.DictCursor)
        while True:
            req, arg, res = self.reqs.get()
            if req=='--close--': break
            cursor.execute(req, arg)
            if res:
                for rec in cursor:
                    res.put(rec)
                res.put('--no more--')
            conn.commit()
        conn.close()
    def execute(self, req, arg=None, res=None):
        self.reqs.put((req, arg or tuple(), res))
    def select(self, req, arg=None):
        res=Queue.Queue()
        self.execute(req, arg, res)
        while True:
            rec=res.get()
            if rec=='--no more--': break
            yield rec
    def close(self):
        self.execute('--close--')

if __name__ == "__main__":
    tab01 = [(23, "запись_1"),
         (24, "запись_2")]
    db=MySQLThread('169.254.64.58')
    for row in db.select('SELECT * FROM tab01'):
        print row['id'], row['name']
    db.close()
    
