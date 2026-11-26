# Installation and usage

Use a fresh Linux host with systemd, Python 3, nginx, Mosquitto and mosquitto-clients. The agent needs Windows and Python with Tk for a source run. Set DNS and obtain certificates for the HTTPS and MQTT endpoints. Replace `pulse.example.test` with your HTTPS hostname and use your own broker hostname. Keep the two certificate chains trusted by the relevant clients.

## 1. Set up MQTT

1. Make a broker password file with `sudo mosquitto_passwd -c /etc/mosquitto/passwd serverpulse_ingest` on a fresh broker. The `-c` flag creates or overwrites the file.
2. Install the contents of `deploy/mosquitto/acl.example` as `/etc/mosquitto/acl`. Give both files owner `root:mosquitto` and mode `0640`.
3. Install `deploy/mosquitto/serverpulse.conf.example` as `/etc/mosquitto/conf.d/serverpulse.conf`. Set its certificate and key paths and ensure the broker can read them. Restart Mosquitto on the fresh host. Limit the external firewall to the required services. Keep the ingestion listener on loopback.
4. Install `serverpulse-provision` and `serverpulse-revoke` from `deploy/mosquitto/` into `/usr/local/sbin/` with `root:root` ownership and mode `0755`. Give the dedicated API service account only these two sudo commands, via `visudo`. For an account named `serverpulse`:

   ```sudoers
   serverpulse ALL=(root) NOPASSWD: /usr/local/sbin/serverpulse-provision "", /usr/local/sbin/serverpulse-revoke ""
   ```

## 2. Start the API and dashboard

1. Place the repo on the host. Give the API account write access to a `database/` directory adjacent to `backend/`. It contains the SQLite file and its WAL files.
2. In `backend/`, run `python3 -m venv .venv`, then `.venv/bin/python -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` in `backend/`. Set `MQTT_PASSWORD` to the ingest password, `PUBLIC_MQTT_HOST` to the broker hostname and `ALLOWED_ORIGINS` to the exact dashboard HTTPS origin. Restrict read access to the config. Keep `SECURE_COOKIE=true` on HTTPS.
4. From `backend/`, run `.venv/bin/python -m uvicorn main_v2:app --host 127.0.0.1 --port 8001` as the API account. Run one instance so the MQTT client ID remains unique.
5. Copy the three files in `frontend/` directly into the document root. Use `deploy/nginx/serverpulse.conf.example` as the site configuration, set your hostname, paths and TLS credentials, verify with `nginx -t`, then reload nginx on the fresh host.
6. Schedule `.venv/bin/python maintenance.py` from `backend/` under the API account. It deletes expired sessions, expired pairing codes and telemetry older than seven days.

## 3. Pair and monitor a Windows device

Run these commands from `agent/` in PowerShell.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
$env:SERVERPULSE_API_URL = 'https://pulse.example.test'
.\.venv\Scripts\python main.py
```

For a private broker CA, set `SERVERPULSE_MQTT_CA` to its CA certificate before starting the agent. For a private HTTPS CA, set `REQUESTS_CA_BUNDLE` to an appropriate CA bundle. Deploy certificates that match the endpoint names.

Register and sign in on the HTTPS dashboard. Generate a pairing code and enter it in the agent within ten minutes. Verify current metrics and history in the dashboard. To remove access, revoke the device from the dashboard, then clear its local pairing in the agent. If broker revocation is reported incomplete, retry it from the dashboard.

To build the installer, install PyInstaller in the agent virtual environment, run it with `ServerPulse.spec`, then compile `setup.iss` with Inno Setup. To enable the download link, publish your built installer on your own web host at `/downloads/ServerPulseSetup.exe`.
