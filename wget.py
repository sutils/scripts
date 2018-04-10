#!/usr/bin/env python
import urllib
import urllib2
import sys
import ssl
import base64
if len(sys.argv) < 2:
    print"Usage: wget url"
    sys.exit(1)
url = sys.argv[1]
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
if url.find("@") > -1:
    parts = url.split("@")
    auth_parts = parts[0].split("//")
    user_pass = auth_parts[1].split(":")
    auth_str = base64.b64encode(
        '%s:%s' % (user_pass[0], user_pass[1]))
    req = urllib2.Request(auth_parts[0] + "//" + parts[1])
    req.add_header("Authorization", "Basic %s" % auth_str)
    response = urllib2.urlopen(req)
    sys.stdout.write(response.read())
    response.close()
else:
    response = urllib2.urlopen(url, context=ctx)
    sys.stdout.write(response.read())
    response.close()
