# Architecture

Open any `.excalidraw` file with Excalidraw's **Open** command to edit the shapes, labels and arrows.

| Diagram | Scope |
| --- | --- |
| [System](diagrams/system.excalidraw) | Windows agent, dashboard, web proxy, broker, API and SQLite |
| [MQTT](diagrams/mqtt.excalidraw) | Publish, topic authorization, validation and persistence |
| [Database ERD](diagrams/database.excalidraw) | Five tables and their foreign keys |
| [Device pairing](diagrams/pairing.excalidraw) | Code issue, exchange, provisioning and local credentials |
| [Security](diagrams/security.excalidraw) | Credential storage, TLS, authorization and revocation |

The browser and agent pair over HTTPS. Telemetry uses `serverpulse/devices/<device_id>/telemetry` over MQTT with QoS 1. Mosquitto gives each device write access to its own topic. The backend subscribes on loopback, validates the device identity and measurement payload, then updates its last-seen timestamp alongside the SQLite telemetry insert.

A pairing code is single-use and valid for ten minutes. SQLite stores a digest of the code and reserves a pending device before broker provisioning. The broker gives the agent a device-specific password, stored locally via Windows Credential Manager through keyring. On revocation the API disables ingestion for the device and calls the broker helper to remove its credentials.

SQLite stores Argon2 account password hashes and digests of session tokens. Dashboard reads are scoped to the signed-in account. The browser sends an HttpOnly, SameSite=Strict session cookie, marked Secure by default. Unsafe authenticated API calls are checked against the configured origin allowlist.

The `users` table has one-to-many relationships with `sessions`, `devices` and `pairing_codes`. Each `telemetry` row belongs to one device. Deletion cascades through these foreign keys. Revocation sets `devices.revoked_at` and disables the device while retaining its history.
