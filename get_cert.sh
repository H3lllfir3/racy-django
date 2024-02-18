#!/bin/bash

set -e

conf_cert() {

    mkdir -p /etc/letsencrypt
    cat > /etc/letsencrypt/cli.ini <<EOF
# Uncomment to use the staging/testing server - avoids rate limiting.
# server = https://acme-staging.api.letsencrypt.org/directory
# Use a 4096 bit RSA key instead of 2048.
rsa-key-size = 4096
# Set email and domains.
email = admin@example.com
domains = example.com, www.example.com
# Text interface.
text = True
# Suppress the Terms of Service agreement interaction.
agree-tos = True
EOF
    certbot certonly --standalone
}

if command -v certbot &> /dev/null
then
    conf_cert
    
else 
    echo "You don't have certbot installed."
    sudo apt install certbot -y
    conf_cert
fi