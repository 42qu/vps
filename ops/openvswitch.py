#!/usr/bin/env python
# coding:utf-8

import _env
from lib.command import call_cmd, CommandException
try: 
    import json
except ImportError:
    import simplejson as json

import ovs.dirs
from ovs.db import error
from ovs.db import types
import ovs.db.idl

def _ovs_db_get_row_val (row, column_name):
    val = getattr (row, column_name) 
    # a little hack for optional values
    if isinstance (val, (list, set)) and row._data[column_name].type.is_optional ():
        if len (val) == 1:
            val = val[0]
        elif len (val) == 0:
            val = None
    return val

def ovs_vsctl (args):
    call_cmd ('ovs-vsctl' + args)

def ovs_db_find (columns, table, cond):
    sock = "unix:/var/run/openvswitch/db.sock"
    schema_file = "%s/vswitch.ovsschema" % ovs.dirs.PKGDATADIR
    schema = ovs.db.schema.DbSchema.from_json(ovs.json.from_file(schema_file))

    #prune schema
    try:
        table_schema = schema.tables[table]
        schema.tables = {table: table_schema}
        verify_columns = []
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

    idl = ovs.db.idl.Idl(sock, schema)
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
            result[column_name] = _ovs_db_get_row_val (row, column_name)
        results.append (result)
        return

    for row in idl.tables[table].rows.itervalues ():
        match = True
        for k, v in cond.iteritems ():
            if _ovs_db_get_row_val (row, k) != v:
                match = False
                break
        if match:
            __append_row (results, row)
    idl.close ()
    return results
    
#def ovs_db_find (columns, table, cond):
#    """ columns is a list, cond is a KV dict """
#    if columns:
#        columns_arg = "--columns=" + ",".join (columns)
#    else:
#        columns_arg = ""
#    cmd = 'ovs-vsctl -- %s  find %s %s' % (
#        columns_arg,
#        table,
#        " ".join (map (lambda v: "%s=%s" % (v[0], v[1]), cond.items()))
#        )
#    out = call_cmd (cmd)
#    results = list ()
#    result = None
#    lines = out.split ("\n")
#    for line in lines:
#        try:
#            if not result:
#                result = dict ()
#            if line.find (":") != -1:
#                arr = line.split (":")
#                result[arr[0].strip ()] = arr[1].strip ()
#            else:
#                results.append (result)
#                result = None
#        except ValueError, e:
#            print arr[1]
#            print line
#            raise CommandException (cmd, "")
#    if result:
#        results.append (result)
#
#    return results

def ovs_db_find_one_by_one (column, table, cond):
    results = ovs_db_find  ([column], table, cond)
    if len (results) == 1:
        val = results[0].get (column)
        if val:
            return val
    raise Exception ("cannot find %s from table %s %s" % (
        column,
        table,
        " ".join (map (lambda v: "%s=%s" % (v[0], v[1]), cond.items()))
        ))

if __name__ == '__main__': 
    import pprint
    pprint.pprint (ovs_db_find ([], "Interface", {'mtu':1500}))
    pprint.pprint (ovs_db_find (['ofport'], "Interface", {'name': 'vps2'}))
    pprint.pprint (ovs_db_find_one_by_one ('ofport', "Interface", {'name': 'vps2'}))


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
