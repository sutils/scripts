#!/usr/bin/env python
from subprocess import check_output
import urllib
import urllib2
import ConfigParser
import os
import sys
import time
import datetime
import logging
import signal
import ssl
import base64

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

#
FORMAT = "%(asctime)s %(filename)s:%(lineno)s %(levelname)s- %(funcName)s:%(message)s"
logging.basicConfig(level=logging.DEBUG, format=FORMAT)

vmlist_cmd = ['vim-cmd', 'vmsvc/getallvms']
create_snapshot_cmd = ['vim-cmd', 'vmsvc/snapshot.create']
list_snapshot_cmd = ['vim-cmd', 'vmsvc/snapshot.get']
remove_snapshot_cmd = ['vim-cmd', 'vmsvc/snapshot.remove']
if os.environ.has_key('PY_TEST') and os.environ['PY_TEST'] == "1":
    vmlist_cmd = ['cat', 'testdata/exsi.vmlist.txt']
    create_snapshot_cmd = ["echo"]
    list_snapshot_cmd = ['cat', 'testdata/exsi.sslist.txt']
    remove_snapshot_cmd = ['echo']
if len(sys.argv) < 3:
    print"Usage exsi.auto.snapshot.task <node name> <task list configure uri> [snapshot max] [workspace]"
    sys.exit(1)

name = sys.argv[1]
tslist_url = sys.argv[2]
ss_max = 30
ws = os.path.expanduser('~')
if len(sys.argv) > 3:
    ss_max = int(sys.argv[3])
if len(sys.argv) > 4:
    ws = sys.argv[4]


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


def getVmSnapshot(vmid):  # list vm snapshot
    cmds = list_snapshot_cmd[:]
    cmds.extend([vmid])
    allss = check_output(cmds).split("\n")[1:]
    sslist = []
    for ss in allss:
        ss = ss.strip()
        if len(ss) < 1:
            continue
        ssinfo = ss.split("-")
        if len(ssinfo) < 2:
            continue
        ss = ssinfo[len(ssinfo) - 1]
        if not ss.startswith("Snapshot Id"):
            continue
        ssinfo = ss.split(":")
        if len(ssinfo) < 2:
            continue
        sslist.extend([ssinfo[1].strip()])
    return sslist
# getVmSnapshot end


def loadConfig():
    config = ConfigParser.ConfigParser()
    config.optionxform = str
    logger = logging.getLogger(__name__)
    for x in range(0, 3):
        try:
            if tslist_url.find("@") > -1:
                parts = tslist_url.split("@")
                auth_parts = parts[0].split("//")
                user_pass = auth_parts[1].split(":")
                auth_str = base64.b64encode(
                    '%s:%s' % (user_pass[0], user_pass[1]))
                req = urllib2.Request(auth_parts[0] + "//" + parts[1])
                req.add_header("Authorization", "Basic %s" % auth_str)
                response = urllib2.urlopen(req)
                config.readfp(response)
            else:
                response = urllib2.urlopen(tslist_url, context=ctx)
                config.readfp(response)
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
            logger.info("start create snapshot on " + option + "/" + vmid)
            snapshot_name = "auto-" + datetime.datetime.fromtimestamp(
                time.time()).strftime('%Y%m%d-%H:%M:%S')
            # do create snapshot
            cmds = create_snapshot_cmd[:]
            cmds.extend([vmid, snapshot_name, "auto"])
            output = check_output(cmds)
            logger.info("create snapshot on " + option + "/" +
                        vmid + " success by\n" + output)
            # do remove old snapshot
            if ss_max > 0:
                sslist = getVmSnapshot(vmid)
                if len(sslist) > ss_max:
                    cmds = remove_snapshot_cmd[:]
                    cmds.extend([vmid, sslist[0]])
                    output = check_output(cmds)
                    logger.info("remove snapshot on " + option + "/" +
                                vmid + "/" + sslist[0] + " success by\n" + output)
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
if config.has_option("conf", "ss_max"):
    ss_max = config.getint("conf", "ss_max")
if config.has_section(name):
    procSection(vmids, config, name, last)
if config.has_section("all"):
    procSection(vmids, config, "all", last)
storeLast(last)
logger.info("exsi.auto.snapshot.task is done")
# all done
