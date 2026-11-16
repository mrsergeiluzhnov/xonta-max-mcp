#!/usr/bin/env bash
# Prove ownership of xonta.ru to the official MCP registry with a DNS TXT record.
# One key and one record cover every ru.xonta/* server (customs, max, ...).
#
#   bash scripts/registry_dns.sh          # step 1: make the key, print the TXT record
#   bash scripts/registry_dns.sh login    # step 2: after the record is live, log in
#
# The key lives in ~/.xonta-registry/key.pem, outside the repo. Keep it secret and back it up:
# losing it means making a new key and replacing the TXT record.
set -euo pipefail

DOMAIN=${DOMAIN:-xonta.ru}
DIR="$HOME/.xonta-registry"
KEY="$DIR/key.pem"

mkdir -p "$DIR" && chmod 700 "$DIR"
if [ ! -f "$KEY" ]; then
  openssl genpkey -algorithm Ed25519 -out "$KEY"
  chmod 600 "$KEY"
  echo "New key: $KEY"
fi

PUBLIC_KEY="$(openssl pkey -in "$KEY" -pubout -outform DER | tail -c 32 | base64)"
RECORD="v=MCPv1; k=ed25519; p=${PUBLIC_KEY}"

if [ "${1:-}" != "login" ]; then
  cat <<EOF

Add this TXT record at the root of $DOMAIN (host/subdomain field empty or "@", not _mcp-registry):

  $RECORD

Other TXT records (SPF etc.) stay as they are. Then check it and log in:

  dig +short TXT $DOMAIN
  bash scripts/registry_dns.sh login
EOF
  exit 0
fi

if ! dig +short TXT "$DOMAIN" 2>/dev/null | tr -d '"' | grep -qF "$RECORD"; then
  echo "The TXT record is not visible yet. Expected:"
  echo "  $RECORD"
  echo "Found:"
  dig +short TXT "$DOMAIN" || true
  echo "Wait a few minutes (TTL) and try again."
  exit 1
fi

PRIVATE_KEY="$(openssl pkey -in "$KEY" -noout -text | grep -A3 'priv:' | tail -n +2 | tr -d ' :\n')"
mcp-publisher login dns --domain "$DOMAIN" --private-key "$PRIVATE_KEY"
echo "Logged in. Now 'mcp-publisher publish' works for any ru.xonta/* server."
