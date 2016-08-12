import os
import json

from exceptions import LBDockError


config = None
_config_file = '/etc/lbdock/lbdock.json'
_home_config_file = os.path.join(os.path.expanduser("~"), ".lbdock.json")
_remote_disabled_cmds = ['journal']
_remote_sudo_cmds = ['start', 'stop', 'refresh', 'destroy', 'load', 'unload', 'proxy', 'prom', 'certs', 'drone']


class LBDockConf(dict):
    def __init__(self, remote=False, config_file=_config_file):
        super(LBDockConf, self).__init__()
        self._config_file = config_file
        self._remote = remote
        self.load()

    def load(self):
        if not self._remote and os.path.exists(self._config_file):
            with open(self._config_file, 'r') as fd:
                try:
                    self.update(json.load(fd))
                except ValueError as e:
                    raise LBDockError("unable to parse config file {}: {}".format(self._config_file, e))
        elif os.path.exists(_home_config_file):
            with open(_home_config_file, 'r') as fd:
                try:
                    self.update(json.load(fd))
                    self['remote_install'] = True
                    self['remote_disabled_cmds'] = _remote_disabled_cmds
                    self['remote_sudo_cmds'] = _remote_sudo_cmds
                    print "remote running enabled"
                except ValueError as e:
                    raise LBDockError("unable to parse config file {}: {}".format(self._config_file, e))
        else:
            raise LBDockError("config file {} or {} not found".format(self._config_file, _home_config_file))

    def field(self, key):
        value = self.get(key)
        if value is not None:
            return value
        else:
            if self.get('remote_install') is True:
                return None
            else:
                raise LBDockError("unable to find key {} in {}".format(key, self._config_file))


config = LBDockConf()


def check_root():
    if not os.geteuid() == 0:
        raise LBDockError("must run as root")


def chown_dir(dire, uid, gid, dir_mode=0775, file_mode=0755,  recurse=True):
    os.chown(dire, uid, gid)
    os.chmod(dire, dir_mode)
    for item in os.listdir(dire):
        item_path = os.path.join(dire, item)
        os.chown(item_path, uid, gid)
        os.chmod(item_path, file_mode)
        if recurse and os.path.isdir(item_path):
            # recurse
            chown_dir(item_path, uid, gid, dir_mode=dir_mode, file_mode=file_mode, recurse=recurse)
