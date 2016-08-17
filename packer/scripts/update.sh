#!/bin/bash
apt-get update
apt-get -y install curl apt-transport-https ca-certificates

apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys 58118E89F3A912897C070ADBF76221572C52609D

echo "deb https://apt.dockerproject.org/repo debian-jessie main" |tee /etc/apt/sources.list.d/docker.list
echo "deb http://ftp.debian.org/debian jessie-backports main" |tee /etc/apt/sources.list.d/backports.list

apt-get update
apt-get -y install htop iotop bmon dstat sudo bzip2 acpid wget curl dkms build-essential nfs-common python python-pip python-jinja2 vim-nox zsh
