import os

import click

from cmd import runcmd


class DockerStats(object):
    def __init__(self):
        self.cpu_usage_percentage = None
        self.mem_usage = None
        self.mem_limit = None
        self.mem_usage_percentage = None
        self.net_io_read = None
        self.net_io_write = None
        self.disk_io_read = None
        self.disk_io_write = None
        self.processes = None


class Docker(object):
    def container_id(self, unit):
        unit = unit.split('.')[0]
        r, o, e = runcmd("docker inspect --format='{{{{.Id}}}}' {}".format(unit))
        if r:
            return None
        if len(o) >= 12:
            return o[:12]
        else:
            return None

    def stats(self, unit):
        unit = unit.split('.')[0]
        r, o, _ = runcmd("docker stats --no-stream {}".format(unit))
        if not r:
            click.echo(o)

    def stats_all(self):
        d = {}
        r, o, _ = runcmd("docker stats --no-stream -a")
        for idx, line in enumerate(o.split('\n')):
            if idx > 0 and line:
                tokens = line.split()
                try:
                    d[tokens[0]] = DockerStats()
                    d[tokens[0]].cpu_usage_percentage = tokens[1]
                    d[tokens[0]].mem_usage = '{} {}'.format(tokens[2], tokens[3])
                    d[tokens[0]].mem_limit = '{} {}'.format(tokens[5], tokens[6])
                    d[tokens[0]].mem_usage_percentage = tokens[7]
                    d[tokens[0]].net_io_read = '{} {}'.format(tokens[8], tokens[9])
                    d[tokens[0]].net_io_write = '{} {}'.format(tokens[11], tokens[12])
                    d[tokens[0]].disk_io_read = '{} {}'.format(tokens[13], tokens[14])
                    d[tokens[0]].disk_io_write = '{} {}'.format(tokens[16], tokens[17])
                    d[tokens[0]].processes = tokens[18]
                except IndexError as e:
                    click.echo("error parsing docker stats: {}".format(e), err=True)
        return d

    def info(self):
        _, o, _ = runcmd("docker info")
        return [x.strip() for x in o.split("\n") if x]

    def execute(self, unit, command):
        u = unit.replace('.service', '').replace('.timer', '')
        if not command:
            cmd = 'docker exec -ti {} sh'.format(u)
        else:
            cmd = 'docker exec -ti {} {} '.format(u, ' '.join(command))
        click.echo("running command {} into {}".format(cmd, unit))
        return os.system(cmd)
