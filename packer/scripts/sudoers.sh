#!/bin/bash
apt-get -y install sudo

# Set up password-less sudo for user lbdock
echo 'lbdock ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/lbdock
chmod 440 /etc/sudoers.d/lbdock

# no tty
echo "Defaults !requiretty" >> /etc/sudoers
