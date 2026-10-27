# Isolated platform-backed web demo

`platform_demo.py` imports the **actual** `inneros_core_runtime.guardian_api_routes` router from an existing InnerOS installation. It does not mount the core app, MCP, telephony, a database administration route or the execution plane.

Prerequisites: an installed InnerOS platform with FastAPI and uvicorn; set `INNEROS_PLATFORM_ROOT` to its pinned `platform/` directory. Start from this repository with `python -m uvicorn deployment.platform_demo:app --host 127.0.0.1 --port 18886`. Only the web shell, recorded sanitized examples and five Guardian API routes are public.

Public safety boundary:
- Synthetic `ap_validation_01` target only; no Bellini access.
- New REAL inference requests return HTTP 409. The UI reads a previously authorized provider receipt.
- Physical authority/approval parameters are denied. Plans remain dry-run.
- Public recovery requires `simulation: true`; no live probe is permitted.
- No telephone call or phone approval is exposed. The button is blocked explicitly.
- Evidence snapshots persist under the service user state directory with mode 0600; no secrets are copied to this repository.

Run the integration boundary tests with `INNEROS_PLATFORM_ROOT=/path/to/platform python -m pytest tests -q`. Without the private platform, standalone CI runs the five public runtime tests and skips the integration tests; do not call skipped tests a platform deployment proof.

Hosting uses a dedicated loopback service and separate Cloudflare Quick Tunnel. It does not edit existing DNS/tunnels or restart production services. Quick Tunnel URLs can change if the tunnel process restarts and have no availability guarantee. Pin release SHAs and publish a fresh URL if it changes. This is a hackathon lab deployment, not high availability.

Rollback: stop and disable only `inneros-nebius-demo-tunnel.service` and `inneros-nebius-demo-api.service` under the user systemd manager; keep evidence and pinned releases. No existing production service is changed by this deployment.
