#!/bin/bash
cat << EOF > /etc/resolv.conf
domain lbdock.local
search lbdock.local
nameserver 172.17.0.1
nameserver 8.8.8.8
EOF

chattr +i /etc/resolv.conf
