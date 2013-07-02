#!/usr/bin/env python
# coding:utf-8

import _env
import os
import conf
assert conf.OVS_DB_SOCK
from lib.command import call_cmd, CommandException
try: 
    import json
except ImportError:
    import simplejson as json

import ovs.dirs
from ovs.db import error
from ovs.db import types
import ovs.db.idl

class OVSDB (object):

    def __init__ (self, sock):
        self.sock = sock

    def _get_row_val (self, row, column_name):
        val = getattr (row, column_name)
        # a little hack for optional values
        if isinstance (val, (list, set)) and row._data[column_name].type.is_optional ():
            if len (val) == 1:
                val = val[0]
            elif len (val) == 0:
                val = None
        return val

    def _check_column (self, schema, columns, table, cond):
        try:
            table_schema = schema.tables[table]
            verify_columns = []
            if cond:
                verify_columns += cond.keys ()
            if columns:
                verify_columns += columns
            else:
                columns = table_schema.columns
            for column_name in verify_columns:
                if column_name not in table_schema.columns:
                    raise Exception ("no column %s in table %s" % (column_name, table))
        except KeyError:
            raise Exception ("no table %s in schema" % (table))


    def find (self, columns, table, cond=None):
        """ which only works in main thread, depends on signal """
        schema_file = "%s/vswitch.ovsschema" % ovs.dirs.PKGDATADIR
        try:
            from ovs.db.idl import SchemaHelper
            schema_helper = SchemaHelper (schema_file)
            schema = schema_helper.get_idl_schema ()
            self._check_column (schema, columns, table, cond)
            idl = ovs.db.idl.Idl(self.sock, schema_helper)
        except ImportError:
            schema = ovs.db.schema.DbSchema.from_json(ovs.json.from_file(schema_file))
            #check schema
            self._check_column (schema, columns, table, cond)
            idl = ovs.db.idl.Idl(self.sock, schema)

        seqno = idl.change_seqno
        while True:
            idl.run()
            if seqno == idl.change_seqno:
                poller = ovs.poller.Poller()
                idl.wait(poller)
                poller.block()
                continue
            break
        results = list ()

        def __append_row (results, row):
            result = dict ()
            for column_name in columns:
                result[column_name] = self._get_row_val (row, column_name)
            results.append (result)
            return

        for row in idl.tables[table].rows.itervalues ():
            match = True
            if cond:
                for k, v in cond.iteritems ():
                    if self._get_row_val (row, k) != v:
                        match = False
                        break
            if match:
                __append_row (results, row)
        idl.close ()
        return results


    def find_one (self, column, table, cond):
        """ find one and the only record of one column """
        results = self.find  ([column], table, cond)
        if len (results) == 1:
            val = results[0].get (column)
            if val:
                return val
        raise LookupError ("cannot find %s from table %s %s" % (
            column,
            table,
            " ".join (map (lambda v: "%s=%s" % (v[0], v[1]), cond.items()))
            ))


class OVSOps (object):

    def __init__ (self):
        self.ovsdb = OVSDB (conf.OVS_DB_SOCK)

    def find_ofport_by_name (self, if_name):
        return self.ovsdb.find_one ('ofport', "Interface", {'name': if_name})

    def set_mac_filter (self, bridge, ofport, ips):
        call_cmd ("ovs-ofctl del-flows %s in_port=%s" % (bridge, ofport))
        if isinstance (ips, basestring):
            ips = [ips]
        for ip in ips:
            call_cmd ("ovs-ofctl add-flow %s in_port=%s,arp,nw_proto=2,nw_src=%s,priority=2,action=normal" % (bridge, ofport, ip))
            call_cmd ("ovs-ofctl add-flow %s in_port=%s,ip,nw_src=%s,priority=2,action=normal" % (bridge, ofport, ip))
        call_cmd ("ovs-ofctl add-flow %s in_port=%s,arp,nw_proto=1,priority=2,action=normal" % (bridge, ofport))
        call_cmd ("ovs-ofctl add-flow %s in_port=%s,priority=1,action=drop" % (bridge, ofport))

    def unset_mac_filter (self, bridge, ofport):
        call_cmd ("ovs-ofctl del-flows %s in_port=%s" % (bridge, ofport))

    def set_traffic_limit (self, if_name, bandwidth):
        """ bandwidth in kbps """
        assert isinstance (bandwidth, int)
        call_cmd ("ovs-vsctl set interface %s ingress_policing_rate=%d" % (if_name, bandwidth))
        if bandwidth > 0:
            call_cmd ("ovs-vsctl set interface %s ingress_policing_burst=%d" % (if_name, 100))
            call_cmd (["ovs-vsctl", "--", "set", "Port", if_name, "qos=@newqos", "--", 
                "--id=@newqos", "create", "qos", "type=linux-htb", "other-config:max-rate=%d" % (bandwidth * 1000), "queues=0=@q0", 
                "--", "--id=@q0", "create", "queue", "other-config:max-rate=%d" % (bandwidth * 1000)
                ])

    def unset_traffic_limit (self, if_name):
        qos_rows = self.ovsdb.find (['qos'], 'Port', {'name': if_name})
        qos = None
        if qos_rows and qos_rows[0].has_key ('qos'):
            qos = qos_rows[0]['qos']
            if qos:
                #qos_uuid = qos.uuid
                call_cmd ("ovs-vsctl -- destroy qos %s -- clear port %s qos" % (if_name, if_name))
                queues = qos.queues.values ()
                if queues:
                    for q in queues:
                        call_cmd ("ovs-vsctl destroy queue %s" % (q.uuid))
#        call_cmd ("ovs-vsctl set interface %s ingress_policing_rate=0" % (if_name))
#        call_cmd ("ovs-vsctl set interface %s ingress_policing_burst=0" % (if_name))

    def del_port_from_bridge (self, bridge, if_name):
        call_cmd ("ovs-vsctl del-port %s %s" % (bridge, if_name)) 

    def add_port_to_bridge (self, bridge, if_name):
        call_cmd ("ovs-vsctl add-port %s %s" % (bridge, if_name))

if __name__ == '__main__': 
    import pprint
    ovsops = OVSOps ()
    #pprint.pprint (ovsops.find_ofport_by_name ('vps2'))
    #pprint.pprint (ovsops.ovsdb.find ([], "Interface", {'mtu':1500}))
    #pprint.pprint (ovsops.ovsdb.find (['ofport'], "Interface", {'name': 'vps2'}))
    #pprint.pprint (ovsops.ovsdb.find_one_by_one ('ofport', "Interface", {'name': 'vps2'}))
    #ovsops.set_traffic_limit ("vps345", 5000)
    #ovsops.unset_traffic_limit ('vps345')

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
