import click

from cmd import runcmd
from utils import config

from exceptions import LetsencryptError


class Letsencrypt(object):
    def __init__(self, email=config.field('letsencrypt_mail_address')):
        self._email = email

    def add(self, vhost):
        command = "certbot certonly --standalone --non-interactive --expand --agree-tos --email {} --pre-hook \"systemctl stop nginx\" \
                   --post-hook \"systemctl start nginx\" {}".format(self._email, "-d " + " -d ".join(vhost))
        r, o, e = runcmd(command)
        click.echo(o)
        if r:
            raise LetsencryptError("error adding cerfificates: {}".format(e))

    def renew(self):
        command = "certbot renew --standalone --non-interactive --pre-hook \"systemctl stop nginx\" --post-hook \
                  \"systemctl start nginx\""
        r, o, e = runcmd(command)
        click.echo(o)
        if r:
            raise LetsencryptError("error renewing cerfificates: {}".format(e))
