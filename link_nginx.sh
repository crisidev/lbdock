#!/bin/sh
set -e

WHOAMI=$(whoami)
if [ "${WHOAMI}" != "root" ]; then
  echo "error: must run as root"
  exit 1
fi

NGX_CONF_DIR="/etc/nginx"
LBDOCK_NGX_CONF_DIR="/etc/lbdock/conf/nginx"

# backing up / deleting
if [ ! -L ${NGX_CONF_DIR}/nginx.conf ]; then
  echo "creating ${NGX_CONF_DIR}/nginx.conf backup (.bak)"
  cp ${NGX_CONF_DIR}/nginx.conf ${NGX_CONF_DIR}/nginx.conf.bak
  echo "removing ${NGX_CONF_DIR}/nginx.conf"
  rm -f ${NGX_CONF_DIR}/nginx.conf
fi
if [ ! -L ${NGX_CONF_DIR}/sites-enabled ]; then
  echo "creating ${NGX_CONF_DIR}/sites-enabled backup (.bak)"
  cp -a ${NGX_CONF_DIR}/sites-enabled ${NGX_CONF_DIR}/sites-enabled.bak
  echo "removing ${NGX_CONF_DIR}/sites-enabled"
  rm -rf ${NGX_CONF_DIR}/sites-enabled
fi

# linking
echo "sym-linking ${LBDOCK_NGX_CONF_DIR}/nginx.conf to ${NGX_CONF_DIR}/nginx.conf"
ln -sf ${LBDOCK_NGX_CONF_DIR}/nginx.conf ${NGX_CONF_DIR}
echo "sym-linking ${LBDOCK_NGX_CONF_DIR}/sites-enabled to ${NGX_CONF_DIR}/sites-enabled"
ln -sf ${LBDOCK_NGX_CONF_DIR}/sites-enabled ${NGX_CONF_DIR}
echo "sym-linking ${LBDOCK_NGX_CONF_DIR}/lbs-enabled to ${NGX_CONF_DIR}/lbs-enabled"
ln -sf ${LBDOCK_NGX_CONF_DIR}/lbs-enabled ${NGX_CONF_DIR}
echo "sym-linking ${LBDOCK_NGX_CONF_DIR}/lua to ${NGX_CONF_DIR}/lua"
ln -sf ${LBDOCK_NGX_CONF_DIR}/lua ${NGX_CONF_DIR}
exit 0
