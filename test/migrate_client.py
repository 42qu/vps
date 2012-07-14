#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import _env
import ops.migrate as migrate
import conf
from lib.log import Log


def main():
    logger =  Log ("migrate_client", config=conf)
    client = migrate.MigrateClient (logger, "127.0.0.1")

    client.sync_partition ("/dev/main/vps274_root")


if "__main__" == __name__:
    main()

