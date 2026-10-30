# InnerOS Infrastructure Guardian
### Physical AI Operator for Real-World Infrastructure
**Nebius × NVIDIA Global AI Hackathon 2026**

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![NVIDIA Open Models](https://img.shields.io/badge/NVIDIA-Open_Models-76B900.svg)](https://build.nvidia.com)
[![Nebius AI Cloud](https://img.shields.io/badge/Nebius-AI_Cloud-00D4B2.svg)](https://nebius.ai)

> **Real infrastructure. NVIDIA intelligence. Human authority.**

---

## Open the working application

**[guardian.creatorcore.ai](https://guardian.creatorcore.ai/)** reads actual existing infrastructure collectors. No synthetic outage replaces an unavailable source in the public workflow.

| Judge action | What actually happens |
|---|---|
| Choose Casa Rafael / Bellini and Read real infrastructure | Reads the existing source, persists an allowlisted snapshot and shows source/retrieval timestamps. Casa: network, cameras/recorders, servers and energy. Bellini: network. |
| View recorded Nemotron result | Reads the real, point-in-time NVIDIA/Nebius response with its provider receipt. This does not perform another generation. |
| Test Nebius connection - no inference | Makes an authenticated GET to the provider model catalog, at most once per minute. It confirms the NVIDIA model is available; no completion request or generated tokens. |
| New inference | Locked until there is a fresh, unused explicit owner credit authorization. Maximum 2,048 output tokens per attempt; no automatic paid retry or top-up. |
| Request owner call | Refreshes the selected source and previews the exact spoken report. The owner approves on authenticated Home Assistant; VoiceOps calls the fixed private mobile alias only after approval. |
| Download PDF | Exports a branded evidence report; source observations, stored model result, provider check or session-owned call audit. No extra inference or call. |

The orbit nodes show actual running/completed/not-run/error states; owner approval has a separate waiting state. **What actually ran?** lists real HTTP requests, response codes and measured durations. There are no invented delays to imitate model work. Reading Wi-Fi does not silently start a model request or a telephone call.

### Acceptance evidence, 30 October 2026

- **Real inference:** NVIDIA Nemotron 3 Nano on Nebius Token Factory, response **chatcmpl-5de01922-537c-4436-b520-de5fda0b2cd0**, 3,404 input / 1,745 output tokens, 25.795 seconds. The exact analyzed snapshots are retained.
- **Real external catalog check:** HTTP 200 at 11:30:16 Ecuador; requested NVIDIA model listed; 0.818 seconds; zero generation requests/tokens.
- **Real owner callback:** **call_308f8268db41d59ec64b6f1f**, owner-authorized at 11:38:30 Ecuador, completed at 11:40:43. Owner explicitly confirmed hearing the Bellini report and its repetition after asking for it. HA and VoiceOps retained completed/verified dispatch evidence.
- **Phone source binding:** the report states the selected site, actual monitor findings and sample time. Greetings and call-purpose questions repeat that immutable context without requiring a local or external LLM. Free-form conversation remains dependent on the local reasoner; this acceptance does not claim unrestricted autonomous dialogue.
- **Validation:** 41 private-platform Guardian tests passed; Guardian and VoiceOps PR CI passed. The phone bridge/transport tests passed, the effective runtime module path was checked, and deployment backups/rollback were retained.

See [sanitized acceptance evidence](examples/verified-live-acceptance-20261030.json) and the [final handoff](GUARDIAN_HANDOFF_CHATGPT_20261030.md). Public physical device mutation remains disabled. A model recommendation or a completed phone call is not proof of device recovery or authorization to reboot equipment.

## 💡 The Core Idea

Large Language Models are brilliant diagnosticians, but giving an external cloud AI direct SSH keys or write credentials to physical switches, APs, and power distribution units is dangerous.

**InnerOS Infrastructure Guardian** bridges this gap:
1. **Cloud Intelligence (Nebius + NVIDIA):** A model returned by the authenticated Nebius Token Factory catalog is selected only when its ID is explicitly NVIDIA/Nemotron. A provider receipt distinguishes real inference from the default local heuristic.
2. **Strict Trust Boundary & Sanitization:** Before leaving the building, private IPs, customer names, and MACs are sanitized. Nebius never receives direct control or credentials.
3. **Local Authority & Governed Execution:** Real source observations and remote inference evidence are separate from execution authority. The public application can request an owner-approved callback; it cannot mutate customer equipment.
4. **Evidence-backed Verification:** The owner-confirmed callback has dispatch and human audibility evidence. Infrastructure observations do not imply that a reboot or recovery was performed.

---

## Offline developer fixture (not the public application)

The following harness exists for reproducible offline tests. It is separate from the real infrastructure workflow above:

```bash
# Clone the repository
git clone https://github.com/Rafa-Innerchispa/inneros-nebius-nvidia-physical-ai-2026.git
cd inneros-nebius-nvidia-physical-ai-2026

# Run the 7-stage Physical AI Workflow Demo
python3 src/demo_runner.py
```

The command above is intentionally reproducible without credentials or network access. Its output says `FAKE_INFERENCE_DRY_RUN_ACTION`, `physical_mutation_applied=false`, and `physical_recovery_verified=false`.

### Optional: authorized live Token Factory inference

First use authenticated `GET /v1/models` to select an available NVIDIA/Nemotron model. A live inference request requires an explicit credit gate:

```bash
export NEBIUS_API_KEY="your_nebius_api_key_here"
export NEBIUS_NVIDIA_MODEL="exact-model-id-returned-by-/models"
export NEBIUS_LIVE_SMOKE_AUTHORIZED=1
python3 src/demo_runner.py --live-inference
```

In the private InnerOS runtime, the key is read from `owner_vault`; it is never supplied as a CLI argument or printed. The public example accepts an environment variable only to remain standalone.

---

## 📐 The 7-Stage Physical AI Workflow

```text
1. Discover      ──> Inspect physical infrastructure state (read-only)
2. Diagnose      ──> Sanitize telemetry & analyze via Nebius × NVIDIA model
3. Recommend     ──> Suggest bounded operational action (reboot or PoE cycle)
4. Policy Gate   ──> Enforce OWNER_APPROVAL_REQUIRED (prevent unauthorized mutations)
5. Local Execute ──> Dispatch action via local UniFi or Grandstream adapter
6. Verify Recov  ──> Label simulated probes; require a real probe for a real claim
7. Evidence      ──> Issue tamper-evident cryptographic receipt
```

---

## 🛡️ Security & Privacy Model

- **No Secrets to Cloud:** Vendor API keys, SNMP community strings, and passwords never leave the local environment.
- **Anonymized Telemetry:** Private subnets (`192.168.x.x`) are transformed into documentation tokens (`10.0.0.x`).
- **Simulate by Default:** All capabilities support `dry_run=True` to stage and preview mutations before applying power cuts or reboots.
- **Honest Provider Gaps:** Operations not supported by upstream APIs (e.g. per-port PoE cycling on cloud-only routers) immediately return explicit `provider_gap` errors.

## Frontend API contract

The sanitized minimum contract is published in [`api-contract.json`](api-contract.json):

- `GET /api/guardian/overview`
- `POST /api/guardian/diagnose`
- `POST /api/guardian/actions/plan`
- `POST /api/guardian/recovery/verify`
- `GET /api/guardian/evidence/{id}`

The action endpoint is plan-only and forces `dry_run=true`. It does not expose live mutation credentials.

## Evidence taxonomy

| Label | Meaning |
|---|---|
| `REAL` | Provider response or real recovery probe produced a receipt |
| `SIMULATED` | Deterministic demo/dry-run; no physical effect |
| `BLOCKED` | Safety, adapter, model, credential, or authorization gate stopped execution |
| `NOT_RUN` | External provider was deliberately not contacted |

---

## 📜 License

Licensed under the Apache License, Version 2.0. See [LICENSE](LICENSE) for details.

## Test the public export

```bash
python3 -m pip install -r requirements-dev.txt
python3 -m pytest tests -q
```

CI runs only offline tests and the dry-run demo; it never uses API keys or cloud credits. The five API routes describe the private integration contract; this standalone export does not expose a physical-control server.

## Verified API examples

See [sanitized HTTP responses](examples/api-http-evidence.json) from five actual requests to an isolated loopback ASGI runtime. This is API-contract evidence; it is not a public deployment, live Nebius inference, or physical-device recovery proof.


## Verified live inference — 27 October 2026

The private InnerOS adapter completed one evidenced real inference using `nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B` on Nebius Token Factory. The [sanitized provider receipt](examples/nebius-live-receipt.json) records 308 input tokens, 692 output tokens, response ID and finish reason. Telemetry was synthetic; no physical action was executed or recovery verified.

This was the second owner-approved attempt. The first failed in response parsing and its usage was not retained. No automatic paid retries were used. The public demo still defaults to offline simulated inference; this receipt does not imply that running it without credentials invokes Nebius.


## Live infrastructure console — 30 October 2026

**Open [Guardian](https://guardian.creatorcore.ai/).** Choose a site and system, then press **Read real infrastructure**. The central circle opens a readable report; the table lists actual observations and source timestamps. Desktop and mobile scrolling are supported.

| Source | Published observations |
|---|---|
| Casa Rafael / Network | 13 allowlisted Home Assistant network signals, including approved AP aliases |
| Casa Rafael / Cameras | 6 camera/recorder signals; this is not a complete physical camera inventory |
| Casa Rafael / Servers | 2 fleet nodes' aggregate service checks; a failed check does not prove a powered-off host |
| Casa Rafael / Energy | Existing inverter/energy-history metrics; only values actually supplied are shown |
| Bellini / Network | 14 targets from the existing Network Guardian MongoDB collector |

These are read-only integrations with existing collectors, not synthetic incident injection. A source failure returns an explicit error instead of fabricated telemetry. Retrieval time is separate from source observation time; unchanged HA entity timestamps are not fresh physical probes. Monitor reachability does not establish the cause of an outage. Private addresses, credentials and private device names are withheld.

### NVIDIA Nemotron

The owner-authorized frontend request analyzed sanitized real Casa and Bellini snapshots with **NVIDIA Nemotron 3 Nano through Nebius Token Factory**. The persisted report contains response ID **chatcmpl-5de01922-537c-4436-b520-de5fda0b2cd0**, **3,404 input / 1,745 output tokens**, a provider receipt hash, snapshot bindings and **25.795 seconds** measured latency. The output limit was 2,048 tokens. No retry or top-up occurred.

**Read recorded Nemotron analysis** displays that point-in-time result; it does not spend credits on each refresh or analyze later readings automatically. The one-shot authorization is consumed and additional requests return HTTP 409. The model recommended reviewing/rebooting an unreachable AP; this is an unverified recommendation, not a confirmed hardware diagnosis or execution permission. **LOCAL_HEURISTIC** remains a separate, explicitly labeled route in the isolated legacy lab API.

### Human-in-the-loop owner calls

**Request owner call** creates a snapshot-bound request in the existing authenticated Home Assistant approval inbox. The owner approves or cancels on their Android. Only the preconfigured owner mobile alias can be called; no public visitor can approve, choose a number, or authorize device mutations.

After approval, the existing VoiceOps service independently consumes the single-use, expiring HA identity proof. Its local voice opens with a short deterministic report from the selected source: site, sample time, observations needing attention, and uncertainty. The exact spoken report is shown in the UI and bound to the approval digest. This narration does not perform another cloud inference. The first generic callback was physically confirmed by the owner. The corrected contextual-report callback was subsequently approved and the owner explicitly confirmed hearing the selected Bellini report and its repetition.

Requests have a persistent ten-minute cooldown, a ten-minute approval expiry and a durable dispatch claim. Interrupted or ambiguous dispatches are not automatically redialed. The web reports approval and execution states separately. No physical device execution endpoint is exposed, and a successful call does not approve a restart or prove recovery.

See [deployment and rollback](deployment/README.md). The earlier synthetic CLI, API examples and video below remain historical/reproducible lab artifacts; they do not represent current live observations.

## Demo video and final handoff

- [English narrated walkthrough, ~97 seconds](media/inneros-guardian-demo-20261027.mp4)
- [English subtitles](media/inneros-guardian-demo-20261027.srt)
- [Video provenance and scope](media/VIDEO_PROVENANCE_20261027.json)
- [Browser E2E evidence](docs/BROWSER_QA_20261027.json)
- [Official submission readiness checklist](docs/SUBMISSION_READINESS_20261027.md)
- [Final deployment and rollback](docs/FINAL_DELIVERY_20261027.md)

The local video is assembled and ready for owner review; no public YouTube URL or final Devpost submission is claimed.
