#!/bin/bash

set -e

read -p "Enter domains (example.com www.example.com): " domains  
read -p "Enter an email: " email

domain_args=""

for domain in $domains; do
  if [ -z "$domain_args" ]; then
    domain_args="$domain" 
  else  
    domain_args="$domain_args, $domain"
  fi
done


conf_cert() {

    mkdir -p /etc/letsencrypt
    cat > /etc/letsencrypt/cli.ini <<EOF
# Uncomment to use the staging/testing server - avoids rate limiting.
# server = https://acme-staging.api.letsencrypt.org/directory
# Use a 4096 bit RSA key instead of 2048.
rsa-key-size = 4096
# Set email and domains.
email = $email
domains = $domain_args
# Text interface.
text = True
# Suppress the Terms of Service agreement interaction.
agree-tos = True
EOF
    certbot certonly --standalone

    for domain in $domains; do

        privkey="/etc/letsencrypt/live/$domain/privkey.pem"
        cert="/etc/letsencrypt/live/$domain/cert.pem"  

        if [ -f $privkey ] && [ -f $cert ]; then
            echo "Found keys for $domain"  
            cp $privkey ./project/privkey.pem
            cp $cert ./project/cert.pem 
        else
            echo "No Let's Encrypt keys found for $domain"
        fi

    done

}

if command -v certbot &> /dev/null
then
    conf_cert
    
else 
    echo "Installing certbot..."
    sudo apt install certbot -y
    conf_cert
fi