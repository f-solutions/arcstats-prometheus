#!/usr/bin/env python3
import logging
import argparse
import bottle
from bottle import route, run, template, response, request
import subprocess
import json
import sys
import os
import ipaddress

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)-15s %(levelname)-8s %(name)-12s %(message)s'
)
logger = logging.getLogger('arcstats-prometheus')

parser = argparse.ArgumentParser(description='dhcp pool stats exporter for prometheus')
parser.add_argument('-l', '--listen-address', required=False, help='listen-address', default='::')
parser.add_argument('-p', '--listen-port', required=False, help='listen-port', default=9991)
parser.add_argument('-R', '--restrict', required=False, help='restrict metrics to set of IP addresses (may repeat)', default=None, action='append')
args = parser.parse_args()

restricted_addresses = []
if args.restrict is not None:
    for restricted_address in args.restrict:
        restricted_addresses.append(ipaddress.ip_address(restricted_address))

def test_address_pair(a, b):
    if a.version == 4 and b.version == 6:
        return (a == b.ipv4_mapped)
    if a.version == 6 and b.version == 4:
        return (a.ipv4_mapped == b)
    return (a == b)

def test_restricted(remote_address):
    addr = ipaddress.ip_address(remote_address)
    if args.restrict is not None:
        allowed = False
        for restrict_address in restricted_addresses:
            if test_address_pair(restrict_address, addr):
                allowed = True
                break
        return allowed
    else:
        return True

@route('/metrics')
def prometheus_metrics(force=False):
    if not force and not test_restricted(request['REMOTE_ADDR']):
        return ''
    fp = open('/proc/spl/kstat/zfs/arcstats')
    skipped_first = False
    stats = []
    for data in fp:
        splitted = data.strip().split()
        if len(splitted) != 3:
            continue
        if not skipped_first:
            skipped_first=True
            continue
        key, uu, value = splitted
        try:
            value = int(value)
        except:
            continue
        stats.append('arcstats_%s %s' % (key, value))
    fp.close()
    return '%s\n' % ('\n'.join(stats))

run(host=args.listen_address, port=9991)
