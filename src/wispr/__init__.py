#!/usr/bin/python
from __future__ import print_function
import argparse
import os
import re
import sys
import time
import xml.sax.saxutils
import urlparse
import requests


MSG_REDIRECT = '100'
MSG_PROXY = '110'
MSG_AUTHENTICATION = '120'
MSG_LOGOFF = '130'
MSG_AUTH_POLL_REPONSE = '140'
MSG_ABORT_LOGIN_RESPONSE = '150'

RES_SUCCESS = '0'
RES_LOGIN_SUCCESS = '50'
RES_LOGIN_FAILED = '100'
RES_AUTH_ERROR = '102'
RES_NETWORK_ADMIN_ERROR = '105'
RES_LOGOFF_SUCCESS = '150'
RES_LOGIN_ABORT = '151'
RES_PROXY_DETECTION = '200'
RES_AUTH_PENDING = '201'
RES_INTERNAL_ERROR = '255'


def parse_wispr(r):
    m = re.search(
            r'<WISPAccessGatewayParam.*?>\s*<(.*?)>(.*)</\1>\s*</WISPAccessGatewayParam>',
            r.content, re.I|re.S)
    data = {}
    if m is None:
        return data
    for (key, value) in re.findall(r'<(.*?)>(.*?)</\1>', m.group(2)):
        if value.startswith('CDATA[['):
            data[key] = value[7:-2]
        else:
            data[key] = xml.sax.saxutils.unescape(value)
    return data


def save_logout_url(url):
    fn = os.path.expanduser('~/.wispr')
    if not url and os.path.exists(fn):
        os.unlink(fn)
    else:
        with open(fn, 'w') as output:
            print(url, file=output)


def load_logout_url():
    fn = os.path.expanduser('~/.wispr')
    try:
        with open(fn, 'r') as input:
            return input.readline().strip()
    except IOError:
        return None


def do_wispr_login(r, username, password):
    data = parse_wispr(r)
    while data['MessageType'] == MSG_PROXY and \
            data['ResponseCode'] == RES_SUCCESS:
        delay = int(data.get('Delay', '0'))
        print('Following proxy redirect with %d seconds delay' % delay)
        if delay:
            time.sleep(delay)
        r = request.get(data.get('NextURL', r.url), verify=False)
        data = parse_wispr(r)

    assert data['MessageType'] == MSG_REDIRECT and \
            data['ResponseCode'] == RES_SUCCESS
    form = {'UserName': username}
    if data.get('VersionHigh') == '2.0':
        print('Attempting WISPr2 login')
        form['WISPrVersion'] = '2.0'
        form['Password'] = password
    else:
        print('Attempting WISPr1 login')
        form['Password'] = password
        form['button'] = 'Login'
        form['FNAME'] = '0'
        form['OriginatingServer'] = 'http://www.google.com'

    print('Submitting credentials to %s' % data['LoginURL'])
    r = requests.post(data['LoginURL'], data=form, allow_redirects=False, verify=False)
    data = parse_wispr(r)
    assert data['MessageType'] == MSG_AUTHENTICATION
    if data.get('ReplyMessage'):
        print('Server says: %s' % data['ReplyMessage'])

    login_results_url = None
    while data['ResponseCode'] == RES_AUTH_PENDING:
        login_results_url = data.get('LoginResultsURL', login_results_url)
        delay = int(data.get('Delay', '0'))
        print('Need to poll for status at %s with %d seconds delay' %
                (login_results_url, delay))
        if delay:
            time.sleep(delay)
        r = requests.get(login_results_url, allow_redirects=False, verify=False)
        data = parse_wispr(r)
        if data.get('ReplyMessage'):
            print('Server says: %s' % data['ReplyMessage'])

    if data['ResponseCode'] == RES_LOGIN_SUCCESS:
        save_logout_url(data.get('LogoffURL'))
        print('Login succeeded')
        return True
    elif data['ResponseCode'] == RES_LOGIN_FAILED:
        print('Login failed')
        return False
    else:
        print('DAMNIT!')
        print(data)


def detect():
    r = requests.get('http://www.google.com', allow_redirects=False, verify=False)
    while r.status_code in [302, 304]:
        if 'WISPAccessGatewayParam' in r.content:
            break
        else:
            r = requests.get(r.headers['Location'], allow_redirects=False, verify=False)
    if 'WISPAccessGatewayParam' not in r.content:
        if 'google' in urlparse.urlparse(r.url).hostname:
            print('Already online, no WISPr detection possible')
        else:
            print('No WISPr gateway found')
        return False
    data = parse_wispr(r)
    print('WISPr location: %s' % data['LocationName'])
    if 'VersionHigh' in data:
        print('Supported WISPr versions: %s to %s' %
                (data['VersionLow'], data['VersionHigh']))
    else:
        print('Supported WISPr versions: %s' % data['AccessProcedure'])
    return True


def wispr_login(username, password):
    r = requests.get('http://www.google.com', allow_redirects=False, verify=False)
    while r.status_code in [302, 304]:
        if 'WISPAccessGatewayParam' in r.content:
            break
        else:
            r = requests.get(r.headers['Location'], allow_redirects=False, verify=False)
    if 'WISPAccessGatewayParam' in r.content:
        return do_wispr_login(r, username, password)
    host = urlparse.urlparse(r.url).hostname
    if 'google' in host:
        print('Already online, aborting')
        return True
    else:
        print('No WISPr gateway detected, aborting')
        return False
    

def wispr_logout():
    logoff_url = load_logout_url()
    if not logoff_url:
        print('No logoff URL known, can not log off', file=sys.stderr)
        return False
    r = requests.get(logoff_url, allow_redirects=False, verify=False)
    if r.status_code not in [200, 302]:
        print('Illegal response to logoff request: %d' % r.status_code,
                file=sys.stderr)
        return False
    data = parse_wispr(r)
    if not data:
        print('No WISPr response found at logoff URL')
        return False
    if data['MessageType'] != MSG_LOGOFF:
        print('Invalid message type for logoff response: %s' %
                data['MessageType'], file=sys.stderr)
        return False
    if data['ResponseCode'] != RES_LOGOFF_SUCCESS:
        if data['ResponseCode'] == RES_INTERNAL_ERROR:
            print ('Internal error from WISPr server')
        else:
            print('Logoff failed, error %s' % data['ResponseCode'])
        return False
    print('Logoff succeeded')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('username', nargs='?')
    parser.add_argument('password', nargs='?')
    parser.add_argument('-L', '--logout', default=False, action='store_true',
            help='Log off')
    parser.add_argument('-D', '--detect', default=False, action='store_true',
            help='Only detect WISPr support')
    options = parser.parse_args()
    if not (options.detect or options.logout or options.password):
        print('You must provide a username and password', file=sys.stderr)
        sys.exit(2)

    try:
        if options.detect:
            return detect()
        elif options.logout:
            wispr_logout()
        else:
            return wispr_login(options.username, options.password)
    except requests.exceptions.ConnectionError as e:
        print('Error connecting to server: %s' % e)
    except KeyboardInterrupt:
        print('Aborting')
        return False

if __name__ == '__main__':
    sys.exit(0 if main() else 1)
