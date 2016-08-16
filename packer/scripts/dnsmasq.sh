#!/bin/bash
apt-get -y install dnsmasq

systemctl enable dnsmasq

cat << EOF > /etc/dnsmasq.conf
# Set up your local domain here
domain=lbdock.local

# Example: The option local=/localnet/ ensures that any domain name query which ends in .localnet will be answered if possible from /etc/hosts or DHCP, but never sent to an upstream server
# don't forward requests (andrewoberstar.com/blog/2012/12/30/raspberry-pi-as-server-dns-and-dhcp)
local=/lbdock.local/

interface=eth1
bind-interfaces

## DNS SERVERS
server=8.8.8.8
server=8.8.4.4

# Max cache size dnsmasq can give us
cache-size=10000

address=/lbdock.local/172.28.128.7
EOF
