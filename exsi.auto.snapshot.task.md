exsi auto create snapshot by configure
===

## Configure File

```.cfg
[conf]
#the max count of snapshot
ss_max=30

[<host name>]
<vm name>=<period time by second>

#all section will be matched by each host
[all]
<vm name>=<period time by second>
```

example:

```.cfg
[conf]
ss_max=10
[all]
vTest-general-0=1000
```

## Usage

### run task once

```.sh
python exsi.auto.snapshot.task.py <host name> <confgiure uri>
```

note: configure uri support http basic auth

### configure crontab on exsi

* download `python exsi.auto.snapshot.task.py` to `/srv/`
* link by `ln -s /srv/exsi.auto.snapshot.task.py /sbin/exsi.auto.snapshot.task`
* add config to `/var/spool/cron/crontabs/root` by

```.sh
0    0    *   *   *   /sbin/exsi.auto.snapshot.task <host name> <configure uri> >> /var/log/exsi.auto.snapshot.task.log 2>&1
```

* restart cron by

```.sh
kill -HUP $(cat /var/run/crond.pid)
/usr/lib/vmware/busybox/bin/busybox crond
grep cron /var/log/syslog.log
```
