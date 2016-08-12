import os
import pwd
import grp
import filecmp
import shutil

import click

from docker import Docker
from utils import config, chown_dir
from cmd import runcmd, runcmd_tail
from exceptions import SystemCtlError


class Unit(object):
    def __init__(self, name, path, status=None, status_code=-1, is_loaded=None, docker_id=None):
        self.name = name
        self.path = path
        self.status = status
        self.status_code = status_code
        self.is_loaded = is_loaded
        self.docker_id = docker_id


class SystemCtl(object):
    def __init__(self):
        self._systemd_dir = '/etc/systemd/system'
        self._unit_types = ('.service', '.timer', '.socket')
        self._dock = Docker()

    def _update_units_status(self):
        for unit in self._units:
            r, _, status = self.status(unit.name)
            unit.status = status
            unit.status_code = r
            unit.is_loaded = self.is_loaded(unit.name)
            unit.docker_id = self._dock.container_id(unit.name)

    def _get_unit_path(self, unit):
        for u in self.search():
            if u.name == unit:
                return u.path
        raise SystemCtlError("unit {} not found inside {}".format(unit, ' '.join(config.field('unit_dir'))))

    def _create_data_dir(self, unit):
            data_path = os.path.join(config.field('data_dir'), unit.split('.')[0])
            if not os.path.exists(data_path):
                click.echo("creating data dir on {}".format(data_path))
                os.makedirs(data_path)
                uid = pwd.getpwnam('root').pw_uid
                gid = grp.getgrnam(config.field('owner_group')).gr_gid
                chown_dir(data_path, uid, gid, dir_mode=0777)

    def search(self, units_only=False):
        self._units = []
        self._units_names = set()
        for directory in config.field('unit_dir'):
            for root, dirnames, filenames in os.walk(directory):
                for filename in filenames:
                    if filename.endswith(self._unit_types):
                        name = os.path.basename(os.path.join(root, filename))
                        if name in self._units_names:
                            raise SystemCtlError("duplicate unit name {}".format(name))
                        self._units_names.add(name)
                        self._units.append(Unit(name, os.path.join(root, filename)))
        if not units_only:
            self._update_units_status()
        return sorted(self._units, key=lambda x: (x.status, x.name))

    def journal(self, unit, lines=10):
        runcmd_tail("journalctl -n {} -fu {}".format(lines, unit))

    def status(self, unit):
        r, o, e = runcmd("systemctl status {}".format(unit))
        for idx, line in enumerate(o.split('\n')):
            if line and idx == 2:
                line_split = line.split()
                if len(line_split) >= 1:
                    return r, o, line_split[1]
        return r, o, None

    def add(self, unit):
        unit_path = self._get_unit_path(unit)
        if unit_path and unit_path != "":
            self._create_data_dir(unit)
            path = os.path.join(self._systemd_dir, unit)
            if not os.path.exists(path) or not filecmp.cmp(path, unit_path):
                click.echo("copying unit {} to {}".format(unit_path, path))
                try:
                    shutil.copyfile(unit_path, path)
                except (IOError, shutil.Error) as e:
                    raise SystemCtlError("error copying unit {} to {}: {}".format(unit_path, path, e))
                finally:
                    self.reload()

        else:
            raise SystemCtlError("unit {} not found in {}".format(unit, config.field('unit_dir')))

    def rm(self, unit):
        path = os.path.join(self._systemd_dir, unit)
        if os.path.exists(path):
            click.echo("removing unit {} from {}".format(unit, path))
            try:
                os.remove(path)
            except OSError as e:
                raise SystemCtlError("error removing unit {} from {}: {}".format(unit, path, e))
            finally:
                self.reload()
        else:
            click.echo("unit {} not found in {}".format(unit, self._systemd_dir))

    def start(self, unit):
        _, _, status = self.status(unit)
        if status != "active":
            r, _, e = runcmd("systemctl start {}".format(unit))
            if r:
                raise SystemCtlError("error starting systemd unit: {}".format(e))
        else:
            click.echo("{} status already active".format(unit))

    def stop(self, unit):
        r, _, e = runcmd("systemctl stop {}".format(unit))
        if r:
            raise SystemCtlError("error stoppint systemd unit: {}".format(e))

    def is_loaded(self, unit):
        r, o, e = runcmd("systemctl list-units")
        for line in o.split('\n'):
            if unit in unicode(line, encoding="latin1"):
                return True
        return False

    def reload(self):
        click.echo("reloading systemd")
        r, _, e = runcmd("systemctl daemon-reload")
        if r:
            raise SystemCtlError("error reloading systemd: {}".format(e))

    def cat(self, unit):
        r, o, e = runcmd("systemctl cat {}".format(unit))
        if r:
            raise SystemCtlError("error getting definition of systemd unit: {}".format(e))
        return o
