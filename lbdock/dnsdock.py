import requests

import click

from utils import config
from exceptions import DNSDockError


class DNSDock(object):
    def __init__(self, url=config.field('dnsdock_url')):
        self._url = url

    def _prepare_json(self, name, ip, proxy=None):
        proxy = proxy if proxy else ''
        return "{}-{}".format(name, ip), {'name': name, 'image': name, 'ip': ip, 'aliases': [], 'proxy': proxy}

    def get_services(self):
        try:
            r = requests.get(self._url)
        except Exception as e:
            raise DNSDockError("error getting services: {}".format(e))
        if r.status_code == 200:
            return r.json().iteritems()
        else:
            raise DNSDockError("error getting services, status code {}".format(r.status_code))

    def add(self, name, ip, proxy):
        click.echo("adding A record {} for {}, proxy: {}".format(ip, name, proxy))
        uid, data = self._prepare_json(name, ip, proxy=proxy)
        r = requests.put("{}/{}".format(self._url, uid), json=data)
        if r.status_code != 200:
            raise DNSDockError("error adding service {}, status code {}".format(uid, r.status_code))

    def rm(self, name, ip):
        click.echo("removing A record {} for {}".format(ip, name))
        uid, data = self._prepare_json(name, ip)
        r = requests.delete("{}/{}".format(self._url, uid))
        if r.status_code != 200:
            raise DNSDockError("error removing service {}, status code {}".format(uid, r.status_code))
