# ServerPulse

ServerPulse collects CPU, memory and disk metrics from Windows devices and turns them into a web dashboard with current status and telemetry history. A Windows agent publishes metrics over MQTT, and a FastAPI service validates, stores and serves them from SQLite.

[Türkçe](README.tr.md) · [Installation and usage](docs/setup.md) · [Architecture](docs/architecture.md)

| Directory | Contents |
| --- | --- |
| `backend/` | Authentication, device lifecycle, MQTT ingestion, SQLite and API |
| `frontend/` | HTML, CSS and JavaScript dashboard |
| `agent/` | Windows desktop agent and installer definitions |
| `deploy/` | Nginx and Mosquitto examples, broker provisioning helpers |
| `docs/` | Setup and editable architecture diagrams |

Pair a device by signing in to the dashboard, generating a one-time code and entering the code and HTTPS server URL in the Windows agent. The dashboard shows latest metrics, history and device status. Use **Revoke** to disable a device and remove its broker credentials.

Telemetry includes the device hostname, OS and local/public IP addresses. The agent queries ipify for its public IP. The maintenance script prunes telemetry older than seven days when scheduled.
