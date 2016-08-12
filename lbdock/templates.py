import os
import shutil
import tempfile

from jinja2 import Environment, FileSystemLoader

import click

from utils import config


class LBDockTmpl(object):
    def __init__(self):
        self._runtime_dir = os.path.join(config.field('config_dir'), 'runtime')
        self._env = Environment(loader=FileSystemLoader(self._runtime_dir), trim_blocks=True)

    def get(self, name):
        return self._env.get_template(name)

    def render(self, template, destination, args):
        tmp = tempfile.mktemp()
        click.echo("rendering template on {}".format(destination))
        render = template.render(args=args, config=config)
        with open(tmp, "w") as fd:
            fd.write(render)
        if not os.path.isdir(os.path.dirname(destination)):
            os.makedirs(os.path.dirname(destination))
        shutil.copyfile(tmp, destination)
        os.remove(tmp)
