import os
import json
import bisect
from pprint import pprint

import click

from dnsdock import DNSDock
from utils import config
from exceptions import DNSDockError


class LBDock(object):
    def __init__(self, url=config.field('dnsdock_url'), domain=config.field('domain')):
        self._used_ports = None
        self._url = url
        self._domain = domain
        self._dock = DNSDock(self._url)

    def _get_user_port_dict(self):
        return {'tcp': [], 'udp': []}

    def _handle_port_conflicts(self, port, proto, vhost=False):
        external_port = 0
        if port == 22:
            external_port = 1022
        elif port == 80:
            external_port = 8080
        elif port == 443:
            external_port = 8443
        else:
            external_port = port
        if vhost and 'git' in vhost:
            external_port = 2222

        while external_port in self._used_ports[proto]:
            click.echo("port {} already used, trying next one".format(external_port))
            if external_port >= 65535:
                raise DNSDockError("error finding free ports: no more free ports")
            external_port += 1
        bisect.insort(self._used_ports[proto], external_port)
        return external_port, port

    def _get_status_dict(self):
        return {
            'name': None,
            'http': None,
            'https': None,
            'tcp': None,
            'udp': None,
            'htaccess': None,
            'cert': None,
            'key': None,
            'prom': None,
            'ssl': None,
            'ip': None
        }

    def _gen_http_settings(self, proxy, status_dict):
        if proxy.get('http'):
            status_dict['http'] = proxy.get('http')
        elif proxy.get('https') and not config.field('letsencrypt'):
            status_dict['http'] = proxy.get('https')

    def _gen_https_settings(self, proxy, status_dict, vhost):
        if proxy.get('https') and config.field('letsencrypt'):
            status_dict['https'] = proxy.get('https')
            cert = os.path.join(config.field('letsencrypt_live_dir'), vhost, 'fullchain.pem')
            key = os.path.join(config.field('letsencrypt_live_dir'), vhost, 'privkey.pem')
            if os.path.exists(cert) and os.path.exists(key):
                status_dict['cert'] = cert
                status_dict['key'] = key
            else:
                status_dict['cert'] = os.path.join(config.field('letsencrypt_live_dir'), self.domain, 'fullchain.pem')
                status_dict['key'] = os.path.join(config.field('letsencrypt_live_dir'), self.domain, 'privkey.pem')
            status_dict['htaccess'] = proxy.get('htaccess')
            status_dict['ssl'] = proxy.get('ssl')

    def _gen_tcp_settings(self, proxy, status_dict, vhost):
        if proxy.get('tcp'):
            status_dict['tcp'] = self._handle_port_conflicts(proxy.get('tcp'), 'tcp', vhost=vhost)

    def _gen_udp_settings(self, proxy, status_dict, vhost):
        if proxy.get('udp'):
            status_dict['udp'] = self._handle_port_conflicts(proxy.get('udp'), 'udp', vhost=vhost)

    def _gen_prom_settings(self, proxy, status_dict):
        if proxy.get('prom'):
            status_dict['prom'] = proxy.get('prom')

    def _parse_proxy_settings(self, dnsdock):
        vhost = None
        status_dict = self._get_status_dict()
        if dnsdock.get('Proxy') is not None and len(dnsdock.get('Proxy')) != 0:
            proxy = json.loads(dnsdock.get('Proxy'))
            vhost = "{}.{}".format(dnsdock.get('Name'), self._domain)
            ip = dnsdock.get('IP') if dnsdock.get('Ip') != u'' else config.field('docker_bridge_ip')
            status_dict['name'] = dnsdock.get('Name')
            status_dict['ip'] = ip
            self._gen_http_settings(proxy, status_dict)
            self._gen_https_settings(proxy, status_dict, vhost)
            self._gen_tcp_settings(proxy, status_dict, vhost)
            self._gen_udp_settings(proxy, status_dict, vhost)
            self._gen_prom_settings(proxy, status_dict)
        return vhost, status_dict

    def generate_services(self):
        services = {}
        for uid, dnsdock in self._dock.get_services():
            self._used_ports = self._get_user_port_dict()
            name, proxy = self._parse_proxy_settings(dnsdock)
            if proxy and name:
                services[name] = proxy
        if config.field('debug'):
            pprint(services)
        return services
