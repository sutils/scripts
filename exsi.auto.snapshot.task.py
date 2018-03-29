#!/usr/bin/env python
from subprocess import check_output
import urllib2
import ConfigParser
import os
import sys
import time
import datetime
import logging
import signal
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

#
FORMAT = "%(asctime)s %(filename)s:%(lineno)s %(levelname)s- %(funcName)s:%(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)

vmlist_cmd = ['vim-cmd', 'vmsvc/getallvms']
snapshot_cmd = ['vim-cmd', 'vmsvc/snapshot.create']
if os.environ.has_key('PY_TEST') and os.environ['PY_TEST'] == "1":
    vmlist_cmd = ['cat', 'testdata/exsi.vmlist.txt']
    snapshot_cmd = ["echo"]
if len(sys.argv) < 3:
    print"Usage exsi.auto.snapshot.task <node name> <task list configure uri> [workspace]"
    sys.exit(1)

name = sys.argv[1]
tslist_url = sys.argv[2]
ws = os.path.expanduser('~')
if len(sys.argv) > 3:
    ws = sys.argv[3]


def getVmList():  # list vm by commond line
    vmlist = check_output(vmlist_cmd)
    vms = vmlist.split("\n")[1:]
    vmids = {}
    for vm in vms:
        vm = vm.strip()
        if len(vm) < 1:
            continue
        vminfo = vm.split()
        if len(vminfo) < 2:
            continue
        vmids[vminfo[1]] = vminfo[0]
    return vmids
# getVmList end


def loadConfig():
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    logger = logging.getLogger(__name__)
    for x in range(0, 3):
        try:
            contents = urllib2.urlopen(tslist_url, context=ctx)
            config.readfp(contents)
            logger.info("load config from %s success", tslist_url)
            break
        except Exception as e:
            logger.exception("load config from %s fail with %s",
                             tslist_url, e.message)
            pass
    return config
# getConfig end


def readLast():
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    logger = logging.getLogger(__name__)
    try:
        config.read([ws + "/.exsi.auto.snapshot.last.cfg"])
        logger.info(ws + "/.exsi.auto.snapshot.last.cfg config is loaded")
    except:
        logger.info(ws + "/.exsi.auto.snapshot.last.cfg config is not found")
    return config
# readLast end


def storeLast(config):
    with open(ws + "/.exsi.auto.snapshot.last.cfg", 'wb') as configfile:
        config.write(configfile)
    logger = logging.getLogger(__name__)
    logger.info(ws + "/.exsi.auto.snapshot.last.cfg config is saved")
# storeLast end


def procSection(vmids, config, section, last):
    tslist = config.items(section)
    logger = logging.getLogger(__name__)
    for task in tslist:
        option = task[0]
        delay = config.getint(section, option)
        if vmids.has_key(option) == False:
            logger.info("do snapshot on " + option +
                        " fail with vmid not found")
            continue
        now = int(time.time())
        passed = now
        if last.has_option(section, option):
            passed = passed - last.getint(section, option)
        if passed < delay:
            logger.info("do snapshot on " + option +
                        " is skipped by passed: %ss", passed)
            continue
        try:
            vmid = vmids[option]
            logger.info("start do snapshot on " + option + "/" + vmid)
            snapshot_name = datetime.datetime.fromtimestamp(
                time.time()).strftime('%Y%m%d-%H:%M:%S')
            # do create snapshot
            cmds = snapshot_cmd[:]
            cmds.extend([vmid, snapshot_name, "auto"])
            output = check_output(cmds)
            logger.info("do snapshot on " + option + "/" +
                        vmid + " success by\n" + output)
            # update last
            if last.has_section(section) == False:
                last.add_section(section)
            last.set(section, option, now)
        except:
            logger.exception("do snapshot on " + option + "/" +
                             vmid + " fail with\n")
# procSection end
logger = logging.getLogger(__name__)
logger.info("start exsi.auto.snapshot.task by ws(%s)", ws)
last = readLast()
config = loadConfig()
vmids = getVmList()
if config.has_section(name):
    procSection(vmids, config, name, last)
if config.has_section("all"):
    procSection(vmids, config, "all", last)
storeLast(last)
logger.info("exsi.auto.snapshot.task is done")
# all done
