# Isolated live infrastructure console

Public URL: https://guardian.creatorcore.ai/ . The deployed service is only
`inneros-nebius-demo-api.service` on Intel. No other service needs restarting.

`platform_demo.py` imports the pinned InnerOS Guardian router and adds curated
read-only source routes. It does not mount the core app, NCP/MCP, database admin,
arbitrary network probes, SIP credentials or device execution endpoints.

## Current contracts

- `GET /api/guardian/live/catalog`: fixed sites/categories; no supplied endpoints.
- `GET /api/guardian/live/readings/{site}/{category}`: Casa network, cameras,
  servers, energy; Bellini network. Existing Atlas reads and the existing Mongo
  collector only. A source failure is HTTP 503, with no synthetic replacement.
- `GET /api/guardian/live/analysis`: the persisted real-infrastructure NVIDIA
  receipt, exact snapshots and readable model result.
- `POST /api/guardian/live/analyze`: explicit server-side one-shot credit grant,
  fixed NVIDIA model, 2,048 output-token maximum and no retries. The current
  grant is consumed; further attempts return 409. No general paid API is enabled.
- `POST /api/guardian/live/call-request`: explicit session-bound request, a source
  snapshot no older than five minutes and a durable ten-minute global cooldown.
  No number, arbitrary narrative, endpoint or device action can be supplied.
- `GET /api/guardian/live/calls/{id}`: session-owned status from the existing HA
  approval authority. Identity, nonce, expiry and cancellation remain in HA.

The contextual-call adapter composes a short spoken report from the selected
allowlisted snapshot, binds its digest, and uses the existing mobile approval
contract. Only after authenticated owner acceptance does the isolated worker
request VoiceOps to call the fixed owner alias. VoiceOps independently consumes
the one-time proof. No SIP/route changes or device permissions are introduced.
The helper reads only named owner/VoiceOps settings in the existing official
Guardian config files, inside Intel; credentials are never printed or committed.

Pending approvals survive an API restart. A durable claim precedes dispatch;
interrupted or ambiguous dispatches are never retried. Such outcomes require
receipt reconciliation, not a new automatic call. Public users cannot approve
their own requests. A completed dispatch is not proof of physical recovery or
authorization for a restart. Actual audibility is confirmed separately by owner.

## Source interpretation

Published values use a strict allowlist. Source timestamps and retrieval times
are separate; HA states can be older than the request. Server aggregate checks
are not a host power detector. Bellini reachability is an existing monitor's
observation, not a confirmed root cause. Values are never filled with invented
faults. Short-lived cache delivery is explicitly labeled.

Legacy lab diagnose/plan/verify routes remain isolated to their synthetic target
and DRY_RUN/SIMULATED operation. They do not control the real sources above.

## Verification and recovery

Run `python -m pip install -r requirements-dev.txt` and `python -m pytest tests -q`.
Set `INNEROS_PLATFORM_ROOT` to the pinned private platform for full integration
tests. Standalone CI skips private-platform-only tests; skipped tests are not
deployment proof. Tests never use cloud credits or place telephone calls.

Release archives are immutable and pinned by SHA. Before deployment, consistently
back up `live.sqlite3`, `workflow.sqlite3`, provider receipts, consumed-budget
markers and the service's release override. Never delete a consumed marker to
enable another paid request. Never deploy during an active contextual dispatch.

Change only the isolated API's WorkingDirectory override, reload user systemd and
restart that API. Verify `/healthz` reports the exact intended release, then check
all five public source combinations. On failure restore the previous release
override and restart only the API; preserve audit databases and provider receipts.
The existing public tunnel, HA, Atlas, VoiceOps and customer equipment are not
reconfigured by this deployment. No high-availability guarantee is claimed.
