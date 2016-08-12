#!/bin/bash

# Clean up
apt-get -y --purge remove linux-headers-$(uname -r) build-essential
apt-get -y --purge autoremove
apt-get -y purge $(dpkg --list |grep '^rc' |awk '{print $2}')
apt-get -y purge $(dpkg --list |egrep 'linux-image-[0-9]' |awk '{print $3,$2}' |sort -nr |tail -n +2 |grep -v $(uname -r) |awk '{ print $2}')
apt-get -y remove --purge bsd-mailx exim4 exim4-base* exim4-config exim4-daemon-light anacron
apt-get -y clean

# Remove history file
unset HISTFILE
rm -rf ~/.bash_history /home/lbdock/.bash_history

# sync data to disk (fix packer)
sync
