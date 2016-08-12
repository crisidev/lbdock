"""A setuptools based setup module.

See:
https://packaging.python.org/en/latest/distributing.html
https://github.com/pypa/sampleproject
"""

from setuptools import setup

import os
import pwd
import grp
import json
import shlex
import shutil
from subprocess import Popen, PIPE

from jinja2 import Environment, FileSystemLoader


here = os.path.abspath(os.path.dirname(__file__))
lua_repos = [
  ('https://github.com/openresty/lua-resty-string', 'lua-resty-string'),
  ('https://github.com/openresty/lua-resty-redis', 'lua-resty-redis'),
  ('https://github.com/knyar/nginx-lua-prometheus', 'nginx-lua-prometheus')
]


class Conf(dict):
    def __init__(self, config_file=os.path.join(here, 'lbdock.json')):
        super(Conf, self).__init__()
        self._config_file = config_file
        self.load()

    def load(self):
        if os.path.exists(self._config_file):
            with open(self._config_file, 'r') as fd:
                self.update(json.load(fd))

    def field(self, key):
        value = self.get(key)
        if value is not None:
            return value

config = Conf()


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


def runcmd(cmd):
    cmd = shlex.split(cmd)
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    out, err = p.communicate()
    if out:
        print out
    if err:
        print err


def create_dirs():
    dirs = [os.path.join(config.field('config_dir'), x) for x in ('conf', 'units')] + \
            [os.path.join(config.field('data_dir'), 'nginx')]
    for dire in dirs:
        if not os.path.exists(dire):
            print "creating directory {}".format(dire)
            os.makedirs(dire)


def render_templates():
    for root, dirnames, filenames in os.walk(os.path.join(here, 'templates')):
        for filename in filenames:
            source = os.path.join(root, filename)
            if root != os.path.join(here, 'templates', 'runtime'):
                source = os.path.join(root, filename)
                dest = os.path.join(config.field('config_dir'),
                                    root.replace(os.path.join(here, 'templates') + '/', ''), filename)
                dest_path = os.path.join(config.field('config_dir'),
                                         root.replace(os.path.join(here, 'templates') + '/', ''))
                if not os.path.exists(dest_path):
                    print "creating directory {}".format(dest_path)
                    os.makedirs(dest_path)
                with open(dest, 'w') as fd:
                    print "rendering template on {}".format(dest)
                    fd.write(Environment(loader=FileSystemLoader('/'), trim_blocks=True).get_template(
                        source).render(config=config))
            else:
                dest = os.path.join(config.field('config_dir'), 'runtime', filename)
                dest_path = os.path.join(config.field('config_dir'), 'runtime')
                if not os.path.exists(dest_path):
                    print "creating directory {}".format(dest_path)
                    os.makedirs(dest_path)
                print "copying runtime template on {}".format(dest)
                shutil.copy(source, dest)


def clone_lua_repos():
    if config.field('nginx_lua_auth'):
        print "cloning lua modules for redis based basic-auth"
        for repo, folder in lua_repos:
            repo_path = os.path.join(config.field('config_dir'), 'conf', 'nginx', 'lua', folder)
            if os.path.exists(repo_path):
                print "{} already present, skip clone".format(repo)
            else:
                cmd = "git clone {} {}".format(repo, repo_path)
                print "running command: {}".format(cmd)
                runcmd(cmd)
    else:
        print "nginx_lua_auth set to false. skip clone"


def install_config():
    if not os.path.exists(os.path.join(config.field('config_dir'), 'lbdock.json')):
        print "installing config file into {}".format(os.path.join(config.field('config_dir'), 'lbdock.json'))
        shutil.copy(os.path.join(here, 'lbdock.json'), os.path.join(config.field('config_dir'), 'lbdock.json'))
    else:
        print "config file found into {}, skip copy".format(os.path.join(config.field('config_dir'), 'lbdock.json'))


def install_default_site():
    shutil.copy(os.path.join(here, 'templates', 'conf', 'nginx', 'index.html'),
                os.path.join(config.field('data_dir'), 'nginx', 'index.html'))


def install_drone_bin():
    print "installing drone binary into {}".format('/usr/local/bin/drone')
    shutil.copy(os.path.join(here, 'bin', 'drone-linux'), '/usr/local/bin/drone')


def install_gogs_conf():
    git_conf_dir = os.path.join(config.field('data_dir'), 'git', 'gogs', 'conf')
    if not os.path.exists(git_conf_dir):
        os.makedirs(git_conf_dir)
        print "copy default gogs app.ini to {}".format(git_conf_dir)
        shutil.copy(os.path.join(config.field('config_dir'), 'conf', 'git', 'app.ini'),
                    os.path.join(git_conf_dir, 'app.ini'))


setup(
    name='lbdock',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='1.0.0',

    description='Nginx Load Balancer cohordinated by DNSDock',

    # The project's main homepage.
    url='https://github.com/crisidev/lbdock',

    # Author details
    author='Matteo Bigoi',
    author_email='bigo@crisidev.org',

    # Choose your license
    license='GPLv2',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',

        # Indicate who your project is intended for
        'Intended Audience :: Developers',
        'Topic :: Software Development :: Build Tools',

        # Pick your license as you wish (should match "license" above)
        'License :: OSI Approved :: MIT License',

        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2.7',
    ],

    # What does your project relate to?
    keywords='deploy build docker dnsdock',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['lbdock'],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=['jinja2', 'envoy', 'click', 'redis'],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    # extras_require={
        # 'dev': ['check-manifest'],
        # 'test': ['coverage'],
    # },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('my_data', ['data/data_file'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    entry_points={
        'console_scripts': [
            'lbdock=lbdock:main',
        ],
    },
)

if not config.field('remote_install'):
    create_dirs()
    render_templates()
    uid = pwd.getpwnam('root').pw_uid
    gid = grp.getgrnam(config.field('owner_group')).gr_gid
    chown_dir(config.field('config_dir'), uid, gid)
    chown_dir(config.field('data_dir'), uid, gid, recurse=False)
    install_default_site()
    clone_lua_repos()
    install_drone_bin()
    install_config()
    install_gogs_conf()
else:
    print "remote install performed, remember to edit and copy lbdock-remote.json into ~/.lbdock.json"
