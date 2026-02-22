# Vultr FMCSA Adapter Setup (Personal Account)

This deploys the hosted FMCSA adapter as a standalone HTTPS service and keeps Streamlit as UI only.

## 1) Provision VPS

- Ubuntu 24.04 LTS
- Minimum `1 vCPU / 2 GB RAM`
- Attach a domain/subdomain (example: `adapter.your-domain.com`)

## 2) Install system packages

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-venv caddy
```

## 3) Create service user and directories

```bash
sudo useradd --system --create-home --home-dir /opt/faxp --shell /usr/sbin/nologin faxp
sudo mkdir -p /opt/faxp/app /opt/faxp/keys /etc/faxp /var/log/faxp
sudo chown -R faxp:faxp /opt/faxp /var/log/faxp
```

## 4) Upload app files

Copy these from your repo to the VPS:

- `/opt/faxp/app/fmcsa_adapter_server.py`
- `/opt/faxp/app/faxp_mvp_simulation.py`
- `/opt/faxp/app/deploy/vultr/fmcsa-adapter.service`
- `/opt/faxp/app/deploy/vultr/Caddyfile.fmcsa-adapter`

## 5) Configure adapter env

```bash
sudo cp /opt/faxp/app/deploy/vultr/fmcsa_adapter.env.example /etc/faxp/fmcsa-adapter.env
sudo chmod 600 /etc/faxp/fmcsa-adapter.env
sudo chown root:root /etc/faxp/fmcsa-adapter.env
sudo nano /etc/faxp/fmcsa-adapter.env
```

Set real values for:

- `FAXP_FMCSA_WEBKEY`
- `FAXP_FMCSA_CLIENT_SECRET`
- `FAXP_FMCSA_ADAPTER_AUTH_TOKEN` (strong random token)
- Verifier signing keys (`ED25519` recommended)

## 6) Install service unit

```bash
sudo cp /opt/faxp/app/deploy/vultr/fmcsa-adapter.service /etc/systemd/system/fmcsa-adapter.service
sudo systemctl daemon-reload
sudo systemctl enable --now fmcsa-adapter
sudo systemctl status fmcsa-adapter --no-pager
```

## 7) Configure Caddy HTTPS

```bash
sudo cp /opt/faxp/app/deploy/vultr/Caddyfile.fmcsa-adapter /etc/caddy/Caddyfile
sudo nano /etc/caddy/Caddyfile   # set your real domain
sudo systemctl reload caddy
sudo systemctl status caddy --no-pager
```

## 8) Smoke test from VPS

```bash
curl -sS https://adapter.your-domain.com/healthz
```

```bash
curl -sS https://adapter.your-domain.com/v1/fmcsa/verify \
  -H "Authorization: Bearer REPLACE_WITH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"mcNumber":"498282"}' | jq
```

Expected response shape:

```json
{
  "payload": { "...": "..." },
  "signature_algorithm": "ED25519",
  "signature_key_id": "verifier-...",
  "signature": "..."
}
```

## 9) Connect Streamlit

Set these in Streamlit secrets:

```toml
FAXP_FMCSA_ADAPTER_BASE_URL="https://adapter.your-domain.com/v1/fmcsa/verify"
FAXP_FMCSA_ADAPTER_AUTH_TOKEN="same_token_used_on_vps"
FAXP_FMCSA_ADAPTER_TIMEOUT_SECONDS="10"
FAXP_FMCSA_ADAPTER_REQUIRE_SIGNED_WRAPPER="1"
```

Then rerun Streamlit flow with:

- Provider: `FMCSA`
- Source: `hosted-adapter`
- MC: `498282`

## 10) Operational notes

- Keep adapter auth token and signing keys out of git.
- Rotate adapter token and signer keys on a schedule.
- Restrict inbound ports to `80/443` only.
- Back up `/etc/faxp/fmcsa-adapter.env` and key material securely.
- Before consortium handoff: redeploy under consortium-owned account and rotate all keys/tokens.
