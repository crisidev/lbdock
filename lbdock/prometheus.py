import os

from utils import config
from templates import LBDockTmpl


class Prometheus(object):
    def _get_dest_file(self):
        return os.path.join(config.field('prometheus_dir'), 'targets', 'lbdock.yml')

    def render(self, args):
        tmpl = LBDockTmpl()
        dest = self._get_dest_file()
        tmpl.render(tmpl.get('lbdock.yml'), dest, args)
