#!/usr/bin/env bash
# Install or update Xonta MAX on the VPS as a systemd service on 127.0.0.1:8766.
# Run as root on the server:  bash deploy_vps.sh
# Then add deploy/nginx-mcp.xonta.ru.conf to the mcp.xonta.ru server block and reload nginx.
set -euo pipefail

APP=/opt/xonta-max
RUN_AS=${XONTA_MAX_USER:-xmax}
SRC=${XONTA_MAX_SRC:-xonta-max-mcp}   # PyPI name, or git+https://github.com/mrsergeiluzhnov/xonta-max-mcp

id "$RUN_AS" >/dev/null 2>&1 || useradd -r -M -d "$APP" -s /usr/sbin/nologin "$RUN_AS"
mkdir -p "$APP" && chown -R "$RUN_AS:$RUN_AS" "$APP"

python3 -m venv --help >/dev/null 2>&1 || { echo "python3-venv is missing: apt install -y python3-venv"; exit 1; }
ss -ltn | grep -q ":8766 " && ! systemctl is-active -q xonta-max && { echo "port 8766 is taken by something else"; exit 1; }
[ -x "$APP/venv/bin/python" ] || sudo -u "$RUN_AS" python3 -m venv "$APP/venv"
sudo -u "$RUN_AS" "$APP/venv/bin/pip" install -q --upgrade pip
sudo -u "$RUN_AS" "$APP/venv/bin/pip" install -q --upgrade "$SRC"

cat > /etc/systemd/system/xonta-max.service <<UNIT
[Unit]
Description=Xonta MAX MCP server
After=network-online.target

[Service]
User=$RUN_AS
WorkingDirectory=$APP
Environment=XONTA_MAX_HOSTED=1
Environment=ALLOWED_HOSTS=mcp.xonta.ru
ExecStart=$APP/venv/bin/xonta-max-mcp --http --host 127.0.0.1 --port 8766
Restart=always
RestartSec=3
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable --now xonta-max
systemctl restart xonta-max
for i in $(seq 1 20); do curl -sf http://127.0.0.1:8766/health >/dev/null && break; sleep 1; done
curl -sf http://127.0.0.1:8766/health && echo || { echo "service did not answer, see: journalctl -u xonta-max -n 30"; exit 1; }
curl -s http://127.0.0.1:8766/.well-known/mcp/server-card.json | python3 -c "import sys,json;d=json.load(sys.stdin);print(d['serverInfo'], len(d['tools']), 'tools')"
