#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import _env
import ops.migrate as migrate
import conf
from lib.log import Log


def main():
    logger =  Log ("migrate_client", config=conf)
    client = migrate.MigrateClient (logger, "10.10.2.6")

    client.sync_partition ("/dev/main/vps274_root")


if "__main__" == __name__:
    main()

