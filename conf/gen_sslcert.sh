#!/bin/sh

mkdir -p private
openssl genrsa -des3 -out private/server.key 1024
if [ $? -ne 0 ]; then exit 1 ;fi
openssl req -new -key private/server.key -out private/server.csr
if [ $? -ne 0 ]; then exit 1 ;fi
cp -f private/server.key private/server.key.org

openssl rsa -in private/server.key.org -out private/server.key

if [ $? -ne 0 ]; then exit 1 ;fi
openssl x509 -req -days 365 -in private/server.csr -signkey private/server.key -out private/server.crt

if [ $? -ne 0 ]; then exit 1 ;fi

cat private/server.key private/server.crt > private/server.pem

echo "*** private/server.pem is generated  ***"
