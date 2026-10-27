# Phone approval integration contract (Nebius Physical AI demo)

Status: **integration pending**. Phone calls are not yet wired into the public web console. Existing telephony in InnerOS must be reused, not duplicated.

## Required flow

1. Guardian detects incident and creates an immutable proposal (site, device, requested capability, exact port if PoE, potential service impact, expires_at).
2. Governance generates a single-use `approval_request_id` tied to authenticated owner, proposal digest, tenant, device, capability, port, and TTL.
3. Telephony adapter requests a call to the enrolled owner number using the established InnerOS phone-approval service. Public frontend must never receive a number, PIN, access token, or callback secret.
4. The owner hears action summary, impact, and an explicit approve/reject choice. No action can execute from an unanswered call, voicemail, silence, DTMF sent by an unauthenticated caller, or a callback without provider-verified signature.
5. Trusted server callback validates telephony provider identity, request freshness, owner verification, nonce, expiry, and exact action digest; it persists APPROVED/REJECTED once. Subsequent retries return the same decision.
6. **Separately** the Capability Gateway checks its policy and consumes the single-use approval reference. It must independently verify target identity and provider support before *any* physical mutation. Phone approval alone never grants unrestricted device control.
7. Live action returns signed/auditable provider receipt; then read-only recovery probe generates a separate verification receipt. If any result missing, status remains NOT_VERIFIED.

## Frontend event shape (proposed, not an existing route)

Read-only event stream or polling may expose sanitized status:
```json
{
  "approval_request_id": "demo-request",
  "channel": "phone",
  "status": "PENDING_CALL",
  "expires_at": "2026-10-27T18:00:00Z",
  "action_digest": "sha256:example",
  "truth": "NOT_VERIFIED"
}
```

States: CREATED, PENDING_CALL, RINGING, ANSWERED_PENDING_DECISION, APPROVED, REJECTED, EXPIRED, CALL_FAILED, CANCELLED.

## Non-negotiable test cases

- Call not answered => no execution.
- Wrong caller identity / spoofed callback => DENIED.
- Duplicate callback / retry => one approval decision and at most one mutation.
- Approval for switch A, port 3 cannot authorize switch B, port 5.
- Approval expires and cannot be replayed.
- If Device Fabric or cloud inference is offline, action fails closed.
- Without provider receipt, do not claim execution; without real recovery probe, do not claim restored.
- Bellini production network: read-only during hackathon demo. Physical demonstration, if any, must use specifically approved lab hardware.
- Cloud Nebius inference receipt and phone approval receipt are independent evidence types. Neither establishes hardware recovery alone.

## Evidence labels

`SIMULATED_PHONE_DECISION` means JavaScript-only reference UI. `REAL_PHONE_AUTHORIZATION` requires the authenticated telephony gateway receipt. `REAL_PHYSICAL_ACTION` requires device provider receipt. `REAL_RECOVERY` requires an actual subsequent health probe.

No real phone-call integration or approval endpoint is implied by this document.
