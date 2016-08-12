import os
import hashlib

import click
import redis

from cmd import runcmd
from utils import config
from exceptions import NginxACLError, NginxVHostError
from templates import LBDockTmpl


class NginxACL(object):
    def __init__(self, host=config.field('redis_host'), port=config.field('redis_port'), db=0):
        self._redis_key_path = 'nginx'
        self._redis_host = host
        self._redis_port = port
        self._redis_db = db
        self._redis = None

    def _hash_pass(self, password):
        return hashlib.sha256(password).hexdigest()

    def connect(self):
        try:
            self._redis = redis.Redis(host=self._redis_host, port=self._redis_port, db=self._redis_db)
        except (redis.exceptions.RedisError,
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError) as e:
            raise NginxACLError("unable to connect to redis: {}".format(e))

    def redis_info(self):
        try:
            return self._redis.info()
        except (redis.exceptions.RedisError,
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError) as e:
            raise NginxACLError("unable to connect to redis: {}".format(e))

    def getkeys(self):
        try:
            return self._redis.keys(self._redis_key_path + '*')
        except (redis.exceptions.RedisError,
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError) as e:
            raise NginxACLError("unable to connect to redis: {}".format(e))

    def getall(self):
        ret = {}
        for hs in self.getkeys():
            ret[hs] = []
            try:
                users = self._redis.hgetall(hs)
            except (redis.exceptions.RedisError,
                    redis.exceptions.ConnectionError,
                    redis.exceptions.TimeoutError) as e:
                raise NginxACLError("unable to connect to redis: {}".format(e))
            for user in users:
                ret[hs].append(user)
        return ret

    def set(self, user, password, vhost):
        try:
            self._redis.hset('{}:{}'.format(self._redis_key_path, vhost), user, self._hash_pass(password))
        except (redis.exceptions.RedisError,
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError) as e:
            raise NginxACLError("unable to connect to redis: {}".format(e))

    def unset(self, user, vhost):
        try:
            self._redis.hdel('{}:{}'.format(self._redis_key_path, vhost), user)
        except (redis.exceptions.RedisError,
                redis.exceptions.ConnectionError,
                redis.exceptions.TimeoutError) as e:
            raise NginxACLError("unable to connect to redis: {}".format(e))


class NginxVHost(object):
    def _get_dest_file(self, flavour):
        destination = None
        if flavour == 'lbs':
            destination = os.path.join(config.field('nginx_dir'), 'lbs-enabled', 'lbs')
        elif flavour in ('http', 'https'):
            destination = os.path.join(config.field('nginx_dir'), 'sites-enabled', flavour)
        else:
            raise NginxVHostError("flavour {} not known".format(flavour))
        return destination

    def render(self, services):
        tmpl = LBDockTmpl()
        tmpl.render(tmpl.get('http'), self._get_dest_file('http'), services)
        tmpl.render(tmpl.get('https'), self._get_dest_file('https'), services)
        tmpl.render(tmpl.get('lbs'), self._get_dest_file('lbs'), services)

    def reload_nginx(self):
        click.echo("checking nginx configuration before reload")
        r, _, e = runcmd("nginx -t")
        if r:
            raise NginxVHostError("nginx test configuration failed: {}".format(e))
        r, _, e = runcmd("service nginx reload")
        if r:
            raise NginxVHostError("unable to reload nginx {}".format(e))
