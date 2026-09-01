#!/bin/sh
set -e

# ── SSL Certificate Auto-Generation & Setup ──────────────────────────────────
SSL_DIR="/etc/ssl/finances"
mkdir -p "${SSL_DIR}"

if [ ! -f "${SSL_DIR}/selfsigned.crt" ] || [ ! -f "${SSL_DIR}/selfsigned.key" ]; then
    echo "==> Generating self-signed SSL certificate for IP/HTTPS access..."
    
    # Generate openssl config with SAN for localhost and IP addresses
    cat > /tmp/openssl_san.cnf << 'EOF'
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = Finances
L = Finances
O = Finances
OU = Dashboard
CN = localhost

[v3_req]
keyUsage = nonRepudiation, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
EOF

    openssl req -x509 -nodes -days 730 -newkey rsa:2048 \
        -keyout "${SSL_DIR}/selfsigned.key" \
        -out "${SSL_DIR}/selfsigned.crt" \
        -config /tmp/openssl_san.cnf \
        2>/dev/null
    
    rm -f /tmp/openssl_san.cnf
    chmod 600 "${SSL_DIR}/selfsigned.key"
    chmod 644 "${SSL_DIR}/selfsigned.crt"
    echo "==> Self-signed certificate generated at ${SSL_DIR}"
else
    echo "==> Existing SSL certificate found at ${SSL_DIR}"
fi

exec "$@"
