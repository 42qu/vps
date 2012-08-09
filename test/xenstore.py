#!/usr/bin/env python2.6

import _env
import pprint
from ops.xen import XenStore

print XenStore.domain_name_id_map ()
#pprint.pprint( XenStore._get_dict ("/local/domain/0/backend/vif/114/0"))
#pprint.pprint( XenStore._get_tree ("/local/domain/0/backend"))


# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4 :
