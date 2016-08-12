import os

import click
import requests
from pprint import pformat
from copy import deepcopy

from cmd import runcmd
from utils import config
from exceptions import DroneError
from templates import LBDockTmpl


class Drone(object):
    def __init__(self, url=config.field('drone_url'), token=config.field('drone_token'),
                 user=config.field('drone_user')):
        self._url = url
        self._token = token
        self._user = user
        self._setup_env_vars()

    def _setup_env_vars(self):
        os.environ['DRONE_TOKEN'] = self._token
        os.environ['DRONE_SERVER'] = self._url

    def _get_repo_ssh_key(self, repo):
        r = requests.get("{}/api/repos/{}/key?access_token={}".format(self.url, repo, self.token))
        if r.status_code == 200:
            return r.text
        else:
            raise DroneError("error fetching {} ssh key".format(repo), err=True)

    def _install_ssh_key(self, key):
        authorized_keys = os.path.join('/home', self._user, '.ssh/authorized_keys')
        if os.path.exists(authorized_keys):
            if key not in open(authorized_keys, 'r').read():
                with open(authorized_keys, 'a') as fd:
                    click.echo("added SSH key to {}".format(authorized_keys))
                    fd.write(key)
            else:
                raise DroneError("key already present on {}".format(authorized_keys))
        else:
            raise DroneError("file {} not found".format(authorized_keys))

    def get_repos(self):
        r, o, e = runcmd("drone repo ls")
        if r:
            raise DroneError("error searcing drone repos: {}".format(e))
        return [x.strip() for x in o.split('\n') if x]

    def add_repo(self, repo):
        if repo not in self.get_repos():
            r, o, e = runcmd("drone repo add {}".format(repo))
            if r:
                raise DroneError("error adding drone repo {}: {}".format(repo, e))
            else:
                click.echo("repo {} registered to Drone/CI".format(repo))
        else:
            click.echo("repo {} already registered on Drone/CI".format(repo))
        self._install_ssk_key(self._get_repo_ssh_key(repo))


def gen_drone_init_files(name, description, docker_image, port, prom, path, repo):
    args = {
        'description': description,
        'docker_image': docker_image,
        'name': name,
        'port': port,
        'prom': prom,
        'domain': config.field('domain'),
        'repo': repo,
        'config_dir': config.field('config_dir'),
        'data_dir': config.field('data_dir')
    }
    click.echo("initializing {} for Drone/CI".format(path))
    click.echo(pformat(args))

    tmpl = LBDockTmpl()
    templates = [
        (tmpl.get('Dockerfile'), os.path.join(path, 'Dockerfile'), args),
        (tmpl.get('drone.yml'), os.path.join(path, '.drone.yml'), args),
        (tmpl.get('REAME.md'), os.path.join(path, 'README.md'), args),
        (tmpl.get('unit.service'), os.path.join(path, '{}.service'.format(name)), args)
    ]
    args_dev = deepcopy(args)
    args_dev['name'] = '{}-devel'.format(name)
    templates.append((tmpl.get('unit.service'), os.path.join(path, '{}-devel.service'.format(name)), args_dev))
    for template in templates:
        tmpl.render(template[0], template[1], template[2])
