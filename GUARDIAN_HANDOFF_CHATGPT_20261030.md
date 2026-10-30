# Guardian delivery and phone verification — 30 October 2026

Owner requested this handoff for ChatGPT. No new agent task, paid inference or
physical operation is authorized by this document.

## Repository and runtime

- Repository: Rafa-Innerchispa/inneros-nebius-nvidia-physical-ai-2026.
- Public application: https://guardian.creatorcore.ai/ .
- Functional code merged in PRs #8, #9, #10. Functional release:
  `dacbbb40e0dd9d5c16f663da4b965c4257d20797`.
- Only `inneros-nebius-demo-api.service` on Intel was restarted. No HA, NCP/MCP,
  VoiceOps, customer equipment, Cloudflare or other production service was changed.
- Immutable releases and SQLite/provider-receipt backups remain in the service
  user's private `inneros-nebius-demo` state and release directories. Rollback
  restores the isolated API release override and retains evidence/audit data.

## Real sources now available in the public UI

Casa Rafael has selectors for network (13 signals), cameras/recorders (6
allowlisted signals, not total installed cameras), servers (2 fleet nodes), and
energy/inverter (6 available metrics at verification time). Bellini network reads
14 targets from the existing Mongo collector. No new network sweep is performed.

The public API uses strict allowlists, opaque asset references and no private IPs,
credentials or private device names. Existing approved AP aliases can be shown.
Source and retrieval timestamps are distinct. HA entity timestamps can be old.
Fleet `ok=false` means failed aggregate service checks, not a powered-off server.
Bellini `not_reachable` is a monitor observation, not a proven hardware failure.
Unavailable sources fail explicitly; no synthetic incident replaces them.

## Real NVIDIA / Nebius evidence

The owner explicitly authorized one new inference over sanitized real readings.
It ran from the frontend and returned:

- Model: `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B`.
- Provider: Nebius Token Factory; REAL, no local fallback.
- Response: `chatcmpl-5de01922-537c-4436-b520-de5fda0b2cd0`.
- Tokens: 3,404 input, 1,745 output; 2,048 output maximum.
- Actual elapsed time: 25.795 seconds. One request, no retries or top-ups.
- The real model recommended rebooting an unreachable AP. This recommendation is
  not a confirmed root cause or physical authorization; no restart was performed.
- The report and exact snapshots persist at `/api/guardian/live/analysis`.
  Subsequent paid requests return 409 because the one-shot marker is consumed.

Do not conflate this with the older synthetic receipts, CLI or October 27 video.

## Governed telephone integration

The public button requests the fixed owner mobile alias; users cannot choose a
number, narrative or physical action. Authenticated Home Assistant identity,
nonce, expiry and one-time approval are reused. VoiceOps independently consumes
the approval proof. A durable local dispatch claim prevents redial after an
interrupted or ambiguous result. A request has ten-minute expiry and cooldown.

The first public generic call, `call_b3b78981b85ec43db6aeec96`, was approved on
Android and the owner confirmed the phone rang and conversation worked. It did
not state the reason, which led to PR #10.

The contextual follow-up, `call_a215ad7008f36b892bc22d47`, binds a specific real
Bellini snapshot and exact spoken text to an approval digest. Its report says:

> Te llamo por la revisión de la red en Bellini. Lectura de las 10:32, hora de
> Ecuador. El monitor no alcanza 2 señales: AP 4, HOST 2. Esto no confirma una
> avería física. Esta llamada solo informa; no autoriza acciones sobre equipos.

Owner confirmed approval, notification and ringing. Owner did **not** confirm
hearing the complete report; they said they spoke at the start and were unsure.
Do not describe the spoken report as owner-verified yet.

The actual VoiceOps receipt shows:

- Dispatched, completed SIP conversation, Piper `es_ES-sharvard-medium.onnx`.
- Opening synthesized before INVITE: 4,186 ms render, 18,564 ms audio.
- Opening started at zero ms after SIP answer. These measurements prove audio
  generation/transmission was attempted, not that the owner heard every word.
- Local Whisper, `stt_external=false`, zero STT errors, two accepted turns.
- Later replies used `deterministic-local-fallback`; the owner heard that the
  principal local reasoner was unavailable. A read-only model-catalog check
  returned `ReadError`. No paid external fallback was used.
- One later barge-in event; no raw transcript persisted. Do not attribute the
  initial report problem conclusively to interruption.

The remaining conversational issue belongs to the existing local VoiceOps/model
dependency. The current delivery scope permits changing only the isolated
Guardian API, so no model service or VoiceOps runtime was restarted/reconfigured.
Device action approval through Guardian's telephone route is still blocked;
calling does not grant permission to restart equipment.

## Validation and evidence

- 33 tests passed with the pinned private platform; both PR #10 CI checks passed.
- Public HTTPS: all five source/category combinations returned 200; unknown site
  422; missing call session/confirmation 403; spent inference authorization 409.
- Desktop and 390×844 mobile UI inspected; readable reports, source switching,
  native scrolling and persisted model receipt checked.
- Intel private evidence files under `inneros_core/var/evidence/`:
  `GUARDIAN_REAL_SOURCES_PUBLIC_20261030.json`,
  `GUARDIAN_REAL_INFRASTRUCTURE_DELIVERY_20261030.json`,
  `GUARDIAN_CONTEXT_CALL_DIAGNOSTIC_20261030.json`.
- Screenshots are also retained in the Codex chat workspace `outputs/`.

Next verification: establish local model availability without changing unrelated
infrastructure, and obtain a separately approved call where the owner listens to
the full opening report. Never reuse an old approval or reset the paid marker.
