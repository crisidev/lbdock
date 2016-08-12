import shlex
from subprocess import Popen, PIPE

import click


def runcmd(cmd, debug=False):
    cmd = shlex.split(cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    r = p.returncode
    if debug:
        click.echo("running command: {}".format(cmd))
        click.echo("command status code: {}".format(r))
        if out:
            click.echo("command stdout: {}".format(out))
        if err:
            click.echo("command stderr: {}".format(err), err=True)
    return r, out, err


def runcmd_tail(cmd, debug=False):
    cmd = shlex.split(cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    for line in iter(p.stdout.readline, ""):
        click.echo(line, nl=False)
    if debug:
        err = p.stderr.read()
        if err:
            click.echo("command stderr: {}".format(err), err=True)
