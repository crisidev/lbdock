import os
import sys
import time
from pprint import pformat
from copy import deepcopy

import click

from utils import check_root, config, LBDockConf
from cmd import runcmd
from lbdock import LBDock
from dnsdock import DNSDock
from drone import Drone, gen_drone_init_files
from docker import Docker, DockerStats
from systemd import SystemCtl
from prometheus import Prometheus
from letsencrypt import Letsencrypt
from nginx import NginxACL, NginxVHost
from exceptions import (LBDockError, DNSDockError, NginxACLError, NginxVHostError,
                        PrometheusError, DroneError, DockerError, SystemCtlError, LetsencryptError)

VERSION = 1.0


@click.group()
@click.option('-r', '--remote/--no-remote', default=False, help='run LBDock against a remote host via SSH')
@click.option('-d', '--debug/--no-debug', default=False, help='enable debug')
def cli(remote, debug):
    if remote:
        global config
        config = LBDockConf(remote=True)
    config['debug'] = debug
    if config.field('remote_install'):
        args = deepcopy(sys.argv)
        if bool(set(args) & set(config.field('remote_disabled_cmds'))):
            click.echo("cmd {} is not enabled on remote execution".format(args[0]))
            sys.exit(0)

        cmd = os.path.basename(args.pop(0))
        if '-r' in args:
            del args[args.index('-r')]

        dest = "{}@{}".format(config.field('ssh_user'), config.field('ssh_host'))
        if bool(set(args) & set(config.field('remote_sudo_cmds'))):
            click.echo("cmd {} requires sudo, forwarding sudo command".format(args[0]))
            cmd = 'sudo ' + cmd

        ssh_cmd = "ssh -p {} {} -t \"{} {}\"".format(config.field('ssh_port'), dest, cmd, ' '.join(args))
        r, o, e = runcmd(ssh_cmd)
        click.echo(o.rstrip())
        if r:
            click.echo(e)
        sys.exit(r)


@cli.command(short_help="show version")
def version():
    click.echo(VERSION)
    sys.exit(0)


@cli.command(short_help='print LBDock units')
@click.option('-u', '--units-only/--no-units-only', default=False, help='Display only unit names')
@click.option('-d', '--docker/--no-docker', default=False, help='Print also Docker stats')
@click.option('-a', '--all/--no-all', default=False, help='Print all units. Default only active units')
def ls(units_only, docker, all):
    d = {}
    s = SystemCtl()
    if not units_only and not docker:
        click.echo("\033[1m{: <30} {: >10} {: >6} {: >8} {: >12} UNIT\033[0m".format('NAME', 'STATUS', 'LOADED',
                                                                                     'EXITCODE', 'CONTAINER'))
    elif docker:
        click.echo("\033[1m{: <30} {: >10} {: >6} {: >8} {: >12} {: >5} {: >20} {: >20} {: >20} {: >6} UNIT\033[0m".format(
            'NAME', 'STATUS', 'LOADED', 'EXITCODE', 'CONTAINER', 'CPU', 'MEMORY (U/L)', 'NET I/O (R/T)', 'DISK I/O (R/W)', 'PROC'))
        d = Docker().stats_all()

    for unit in s.search(units_only):
        if all or units_only or unit.status == 'active':
            if not units_only and not docker:
                click.echo("{: <30} {: >10} {: >6} {: >8} {: >12} {}".format(unit.name, unit.status, unit.is_loaded,
                                                                             unit.status_code, unit.docker_id, unit.path))
            elif docker:
                if not d.get(unit.docker_id):
                    d[unit.docker_id] = DockerStats()
                click.echo("{: <30} {: >10} {: >6} {: >8} {: >12} {: >5} {: >20} {: >20} {: >20} {: >6} {}".format(
                    unit.name, unit.status, unit.is_loaded, unit.status_code, unit.docker_id,
                    d[unit.docker_id].cpu_usage_percentage, "{}/{}".format(d[unit.docker_id].mem_usage,
                                                                           d[unit.docker_id].mem_limit),
                    "{}/{}".format(d[unit.docker_id].net_io_read, d[unit.docker_id].net_io_write),
                    "{}/{}".format(d[unit.docker_id].disk_io_read, d[unit.docker_id].disk_io_write),
                    d[unit.docker_id].processes, unit.path))

            else:
                click.echo(unit.name)


@cli.command(short_help='get systemd unit definition')
@click.argument('unit', nargs=-1)
def cat(unit):
    s = SystemCtl()
    for u in unit:
        click.echo("getting definition of for unit \033[1m{}\033[0m:\n".format(u))
        val = s.cat(u)
        if val:
            click.echo(s.cat(u))


@cli.command(short_help='get unit status systemd')
@click.argument('unit')
@click.option('-d', '--docker/--no-docker', default=True, help='Print also Docker stats')
def status(unit, docker):
    s = SystemCtl()
    d = Docker()
    click.echo("getting status for unit \033[1m{}\033[0m:\n".format(unit))
    if docker:
        click.echo(d.stats(unit))
    r, o, e = s.status(unit)
    click.echo(o)
    if r:
        click.echo(e, err=True)
    sys.exit(r)


@cli.command(short_help='read unit journal systemd')
@click.argument('unit')
@click.option('-l', '--lines', default="10", help='Lines of hostory to print before tailing')
def journal(unit, lines):
    s = SystemCtl()
    click.echo("reading journal for unit \033[1m{}\033[0m:\n".format(unit))
    s.journal(unit, lines)


@cli.command(name='exec', short_help='exec a command inside a docker container')
@click.argument('unit')
@click.argument('command', nargs=-1)
def execute(unit, command):
    d = Docker()
    return d.execute(unit, command)


@cli.command(short_help='start systemd unit')
@click.argument('unit', nargs=-1)
def start(unit):
    check_root()
    s = SystemCtl()
    for u in unit:
        click.echo("starting unit \033[1m{}\033[0m".format(u))
        s.add(u)
        s.start(u)


@cli.command(short_help='stop systemd unit')
@click.argument('unit', nargs=-1)
def stop(unit):
    check_root()
    s = SystemCtl()
    for u in unit:
        click.echo("stopping unit \033[1m{}\033[0m".format(u))
        s.stop(u)


@cli.command(short_help='refresh systemd unit, reload proxy')
@click.argument('unit')
def refresh(url, unit, unit_dir, domain, resolver, nginx_site_dir, prom_target_dir):
    check_root()
    s = SystemCtl()
    d = Docker()
    l = LBDock()
    n = NginxVHost()
    click.echo("stopping unit \033[1m{}\033[0m".format(unit))
    s.stop(unit)
    time.sleep(5)
    click.echo("starting unit \033[1m{}\033[0m".format(unit))
    s.add(unit)
    s.start(unit)
    time.sleep(10)
    click.echo("getting status for unit \033[1m{}\033[0m:\n".format(unit))
    click.echo(d.stats(unit))
    r, o, e = s.status(unit)
    click.echo(o)
    if r:
        click.echo(e, err=True)
    click.echo("updating nginx loadbalancer")
    services = l.generate_services()
    n.render(services)
    click.echo("services:\n" + pformat([x for x in services.keys() if services[x].get('https')
                                        or services[x].get('http') or services[x].get('tcp')
                                        or services[x].get('udp')]))
    click.echo("updating prometheus monitoring")
    p = Prometheus()
    p.render(services)
    click.echo("services:\n" + pformat([x for x in services.keys() if services[x].get('prom')]))


@cli.command(short_help='stop systemd unit and unload unitfile')
@click.argument('unit', nargs=-1)
def destroy(unit):
    check_root()
    s = SystemCtl()
    for u in unit:
        click.echo("destroying unit \033[1m{}\033[0m".format(u))
        s.stop(u)
        s.rm(u)


@cli.command(short_help='load systemd unit')
@click.argument('unit', nargs=-1)
def load(unit):
    check_root()
    s = SystemCtl()
    for u in unit:
        click.echo("loading unit \033[1m{}\033[0m".format(u))
        s.add(u)


@cli.command(short_help='unload systemd unit')
@click.argument('unit', nargs=-1)
def unload(unit, unit_dir):
    check_root()
    s = SystemCtl()
    for u in unit:
        click.echo("unloading unit \033[1m{}\033[0m".format(u))
        s.rm(u)


@cli.command(short_help='check if unit is loaded into systemd')
@click.argument('unit')
def isloaded(unit):
    s = SystemCtl()
    if s.is_loaded(unit):
        click.echo("unit {} loaded".format(unit))
        sys.exit(0)
    else:
        click.echo("unit {} not loaded".format(unit), err=True)
        sys.exit(1)


@cli.command(short_help='reload http/https/tcp proxy')
def proxy():
    check_root()
    click.echo("updating prometheus monitoring")
    l = LBDock()
    n = NginxVHost()
    services = l.generate_services()
    n.render(services)
    click.echo("services:\n" + pformat([x for x in services.keys() if services[x].get('https')
                                        or services[x].get('http') or services[x].get('tcp')
                                        or services[x].get('udp')]))
    n.reload_nginx()


@cli.command(short_help='reload prometheus targets')
def prom():
    check_root()
    click.echo("updating prometheus monitoring")
    l = LBDock()
    p = Prometheus()
    services = l.generate_services()
    p.render(services)
    click.echo("services:\n" + pformat([x for x in services.keys() if services[x].get('prom')]))


@cli.group('acl', short_help="manage proxy basic auth")
def acl():
    pass


@acl.command(name='ls', short_help="list current access lists")
def ls_access():
    a = NginxACL()
    a.connect()
    acl = a.getall()
    click.echo("\033[1m{: <30} {}\033[0m".format('VHOST', 'USERS'))
    for vhost, users in acl.iteritems():
        click.echo("\033[1m{: <30} {}\033[0m".format(vhost, ','.join(users)))


@acl.command(name='set', short_help="set acl to vhost")
@click.option('-u', '--user', help='User to add', required=True)
@click.option('-v', '--vhost', help='Virtualhost to manage', required=True)
@click.option('-p', '--password', prompt=True, hide_input=True, confirmation_prompt=True,
              help="User password", required=True)
def set_access(user, password, vhost):
    a = NginxACL()
    a.connect()
    a.set(user, password, vhost)


@acl.command(name='del', short_help="remove acl to vhost")
@click.option('-u', '--user', help='User to add', required=True)
@click.option('-v', '--vhost', help='Virtualhost to manage', required=True)
def del_access(user, vhost):
    a = NginxACL()
    a.connect()
    a.unset(user, vhost)


@cli.group('certs', short_help="manage Letsencrypt SSL certs")
def certs():
    pass


@certs.command(name='add', short_help='add new Letsencrypt SSL cert')
@click.argument('vhost', nargs=-1)
def certadd(vhost):
    check_root()
    l = Letsencrypt()
    n = NginxVHost()
    l.add(vhost)
    services = l.generate_services()
    n.render(services)
    click.echo("services:\n" + pformat([x for x in services.keys() if services[x].get('https')
                                        or services[x].get('http') or services[x].get('tcp')
                                        or services[x].get('udp')]))
    click.echo("updating prometheus monitoring")


@certs.command(name='renew', short_help='renew all Letsencrypt SSL certs')
def certrenew():
    check_root()
    l = Letsencrypt()
    n = NginxVHost()
    l.renew()
    services = l.generate_services()
    n.render(services)
    click.echo("services:\n" + pformat([x for x in services.keys() if services[x].get('https')
                                        or services[x].get('http') or services[x].get('tcp')
                                        or services[x].get('udp')]))
    click.echo("updating prometheus monitoring")


@cli.group('dns', short_help="manage DNS settings")
def dns():
    pass


@dns.command(name='ls', short_help='print DNS configuration')
@click.option('-p', '--porcelaine/--no-porcelaine', default=False, help='Raw print')
def dns_ls(porcelaine):
    dock = DNSDock()
    if not porcelaine:
        print("\033[1m{: <30} {: <25} {: <15} {: >5} PROXY\033[0m".format('ID', 'NAME', 'ADDRESS', 'TTL'))
    for proxy, value in sorted(dock.get_services()):
        if porcelaine:
            click.echo(proxy)
            click.echo(pformat(value))
        else:
            click.echo("\033[1m{: <30} {: <25} {: <15} {: >5} {}".format(proxy[:30], value.get('Name'), value.get('IP'),
                                                                         value.get('Ttl'), value.get('Proxy')))


@dns.command(name='add', short_help="add new DNS name")
@click.option('-n', '--name', help='DNS name without domain')
@click.option('-i', '--ip', help='IP address for A record')
@click.option('-p', '--proxy', default=None, help='Proxy value')
def dns_add(url, name, ip, proxy):
    dock = DNSDock(url)
    dock.add(name, ip, proxy)


@dns.command(name='del', short_help="delete DNS name")
@click.option('-n', '--name', help='DNS name without domain')
@click.option('-i', '--ip', help='IP address for A record')
def dns_del(url, name, ip):
    dock = DNSDock(url)
    dock.rm(name, ip)


@cli.group('drone', short_help="manage Drone/CI settings")
def drone():
    pass


@drone.command(name='ls', short_help="list Drone/CI repositories")
def drone_ls():
    d = Drone()
    click.echo('DRONE-REPO')
    for repo in d.get_repos():
        click.echo(repo)


@drone.command(name='add', short_help="add Drone/CI repository")
@click.argument('repository', nargs=-1)
def drone_add(repository):
    check_root()
    d = Drone()
    for repo in repository:
        click.echo("adding repo \033[1m{}\033[0m to Drone/CI".format(repo))
        d.add_repo(repo)


@drone.command(name='init', short_help="init a Drone/CI repository")
@click.argument('name')
@click.option('-d', '--description', default='Service Description', help='Service Description')
@click.option('-i', '--docker-image', default='user/image:tag', help='Docker image')
@click.option('-P', '--port', default='5000', help='Proxy port')
@click.option('-p', '--prom', default=None, help='Enable Prometheus monitoring')
@click.option('-r', '--repo', default='user/repo', help='Git repo')
@click.option('--path', default=os.getcwd(), help='Directory to initialize')
def drone_init(name, description, docker_image, port, prom, path, repo):
    gen_drone_init_files(name, description, docker_image, port, prom, path, repo)


def main():
    try:
        cli()
    except (LBDockError, DNSDockError, NginxACLError, NginxVHostError,
            PrometheusError, DroneError, DockerError, SystemCtlError, LetsencryptError) as e:
        print "error: {}".format(e)
        sys.exit(1)
    sys.exit(0)


if __name__ == '__main__':
    main()
