import hashlib

import redis

from exceptions import NginxACLError


class NginxACL(object):
    def __init__(self, host, port, db=0):
        self._redis_key_path = 'nginx'
        self._redis_host = host
        self._redis_port = port
        self._redis_db = db
        self._redis = None

    def _hash_pass(password):
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
            self._redis.hset('{}:{}'.format(self._redis_key_path, vhost), user, self.hash_pass(password))
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
