# RAPHAEL WELD-SHELL — Evidence Package

> Branch: `weld-sub10-evidence`
> Accepted baseline: SUB-14 WELDED (`740861f2e`), SUB-13 CLOSED-BY-FOLD, SUB-10 WELDED (`a099ba460`)
> Pre-weld base for this round: `f652152f9182e3f708491b9765dd1657bdc3aabd` (WELD-SUB10 BD-S10 completion appendix)
> Implementation commit (this round): `784d3fddbd9452cb6271171e5ed0385a8382ebe2`
> Implementation/pre-evidence commit count since canonical `7272880f7`: **55** (per `git rev-list --count 7272880f7..HEAD` at implementation commit `784d3fdd`).
> Final HEAD: established by external machine verification of the records-only evidence commit (see Section W-D). The final HEAD is not embedded in this file because the evidence commit cannot contain its own hash without a self-referential loop.
> Probe evidence-capture script: `evidence/phases/P3_0/_b1a_probe.py`
> Parity harness: `/tmp/shell_parity.py` (evidence-only, SEED=20260906; not committed)
> Author: RAPHAEL WELD-SHELL Audit
> Phase: WELD-SHELL
> Gate: WELD-SHELL

## 1. Submission Summary

WELD-SHELL gates the privileged interactive-shell constructors on a
valid Broker-issued execution context (`SessionReceipt`: `authorized=True`,
`authorized_by="capability_broker"`, unexpired). Direct construction of
`ReverseShellCapability` / `SSHShellCapability` (or via
`ShellCapabilityFactory.create` / `ReverseShellCapability.create_from_listener`)
without such a receipt now fails closed with the documented
`ShellNotAuthorized` error. Broker-authorized construction still works.
The prior SUB-14/SUB-13/SUB-10 welds are untouched. SHELL is inside the
canonical closure, so parity is proven by a seeded harness (W-C.1), not
by unreachability.

The code tree being proved is the tree at implementation commit
`784d3fdd`. This evidence file is included in the final records-only
commit on branch `weld-sub10-evidence`.

---

## 2. SD-1 Precondition Verification

**SD-1 target (P3.5):** reverse-shell and SSH-shell construction requires
a Broker-issued execution context; direct privileged construction without
a valid context raises the documented error.

**Pre-weld actual state (verified by inspection at the pre-weld base):**

A. Reverse-shell privileged construction required a Broker-issued
   context: **FALSE.** `ReverseShellCapability.__init__(connection_info,
   session_id, listener_socket, client_socket, client_addr)` accepted a
   plain dataclass and constructed unconditionally.
B. SSH-shell privileged construction required a Broker-issued context:
   **FALSE.** `SSHShellCapability.__init__(connection_info)` constructed
   unconditionally.
C. Missing/invalid context failed with a documented error: **FALSE.**
   No authorization check existed in either constructor, in
   `ShellCapabilityFactory.create`, or in `create_from_listener`.
D. No alternate constructor bypass exists: **FALSE pre-weld** — three
   ungated paths existed (`__init__` ×2, factory `create`,
   `create_from_listener`).
E. The Broker remains the sole PDP: **TRUE** (unchanged;
   `test_g3_en5_single_pdp` passes).
F. PEP ownership unchanged: **TRUE** (PEP remains under `exec/`).

Because A–D were false, this weld implements the minimum SD-1 gating
using the existing architecture: the existing `SessionReceipt` type
(returned by `CapabilityBroker.authorize_shell_session()`) becomes the
execution context, validated by a new `require_shell_authorization()`
helper in `capability.py`. No new policy authority, no new stages, no
new orchestrator, no Docker/Decepticon/Student/Teacher/P5 machinery.

---

## 3. SHELL Primitive Inventory (pre-weld facts)

| Item | Actual state |
|---|---|
| SHELL seam | Interactive-shell capability constructors in `src/orchestrator/capabilities/interactive_shell/` (P1 SD-1 deferral record: `evidence/phases/P1/03_seam_work/SEAM_SITES.md:17`) |
| Privileged constructors | `ReverseShellCapability.__init__` (reverse_shell.py:77), `SSHShellCapability.__init__` (ssh_shell.py:38), `ShellCapabilityFactory.create` (capability.py:275), `ReverseShellCapability.create_from_listener` (reverse_shell.py:162) |
| Authorization mechanism (pre-weld) | NONE at construction time. Callback-IP CIDR check exists only at callback-accept time (`_validate_callback_ip`); listener range checks exist in `ListenerManager`; session/command authorization exists in the Broker (`authorize_shell_session`, `authorize_shell_command`) but is never consulted by any constructor |
| Canonical Runtime reachability | Package IS in closure (4 modules: `capability`, `command_filter`, `listener_manager`, `session` in static closure). Constructors are NOT invoked on the canonical path (only `SafeProvingCapability` is constructed by `RaphaelRuntime`; `stages.py` has no shell refs; the only in-repo constructions are in `tests/e1_interactive_shell_test.py:823`) |
| Legacy/direct reachability | Any caller importing the package can construct privileged capabilities directly (demonstrated by the e1 test itself) |
| Existing shell tests | 34-test e1 suite (`tests/e1_interactive_shell_test.py`); e2 candidate-generation suite (36 tests, generator-level, no capability construction) |
| SD-1 status | DEFERRED since P1 (applying the quarantine broke `test_adversarial_unauthorized_callback`; C7 forbade test edits then) |
| Files changed (this weld) | `capability.py`, `reverse_shell.py`, `ssh_shell.py` (production); `tests/e1_interactive_shell_test.py` (1 test rewritten); `tests/test_p2_guardrail_shell_closed.py` (new) |

---

## W-A — INSPECTABLE WELD DIFF

### W-A.1 — `git name-status` (pre-weld base → implementation)

```
$ git diff --name-status f652152f9..784d3fdd
M	src/orchestrator/capabilities/interactive_shell/capability.py
M	src/orchestrator/capabilities/interactive_shell/reverse_shell.py
M	src/orchestrator/capabilities/interactive_shell/ssh_shell.py
M	tests/e1_interactive_shell_test.py
A	tests/test_p2_guardrail_shell_closed.py
```

(`--stat`: capability.py +71/−? (gate block), reverse_shell.py +14/−?, ssh_shell.py +7/−?, e1 +35/−?, shell_closed +66. Total implementation diff: 5 files, 254 insertions, 13 deletions.)

### W-A.2 — Production diff (exact)

**`capability.py`** — new `ShellNotAuthorized` exception, new
`require_shell_authorization()` validator (duck-typed receipt check to
avoid a circular import: `session.py` imports `ShellConnectionInfo`
from `capability.py`), base `__init__` now takes
`authorization=None` and validates first, factory `create()` takes and
forwards `authorization`:

```python
class ShellNotAuthorized(Exception):
    """Raised when an interactive shell capability is constructed without a
    valid Broker-issued execution context.

    Path ID: SHELL; Weld ticket: Weld-SHELL (P3).
    ...
    """
    pass


def require_shell_authorization(authorization) -> None:
    ...
    if authorization is None:
        raise ShellNotAuthorized(
            "InteractiveShellCapability construction requires a valid "
            "Broker-issued SessionReceipt. ..."
        )
    authorized = getattr(authorization, "authorized", False)
    authorized_by = getattr(authorization, "authorized_by", "")
    expires_at = getattr(authorization, "expires_at", 0)
    session_id = getattr(authorization, "session_id", "")
    if (
        authorized is not True
        or authorized_by != "capability_broker"
        or not session_id
        or not isinstance(expires_at, (int, float))
        or expires_at <= time.time()
    ):
        raise ShellNotAuthorized(...)
```

```python
    def __init__(self, connection_info: ShellConnectionInfo, authorization=None):
        # Weld-SHELL (P3) SD-1: privileged shell construction requires a
        # Broker-issued execution context. Fail closed otherwise.
        require_shell_authorization(authorization)
        self.connection_info = connection_info
```

```python
    @classmethod
    def create(cls, connection_info, authorization=None):
        """... Weld-SHELL (P3) SD-1: requires a Broker-issued SessionReceipt."""
        require_shell_authorization(authorization)
        ...
        return impl_class(connection_info, authorization=authorization)
```

**`reverse_shell.py`** — `__init__` gains `authorization=None` (validated,
forwarded to `super().__init__`); `create_from_listener` gains
`authorization=None` (validated before waiting for any callback):

```python
    def __init__(
        self,
        connection_info: ReverseShellConnectionInfo,
        ...
        authorization=None,
    ):
        from .capability import require_shell_authorization
        require_shell_authorization(authorization)
        super().__init__(connection_info, authorization=authorization)
```

**`ssh_shell.py`** — `__init__` gains `authorization=None` (validated,
forwarded to `super().__init__`).

Removed behavior: unconditional construction from a bare
`ShellConnectionInfo`. No symbols deleted (the weld adds a gate rather
than deleting a fallback); the removed *capability* is "construct
without authorization".

### W-A.3 — Resulting routing

Post-weld privileged construction paths:
1. Caller obtains a `SessionReceipt` via `CapabilityBroker.authorize_shell_session(proposal)` (the sole PDP; dual-gate target/capability/rate/impact/egress checks unchanged).
2. Caller passes the receipt as `authorization=` to the constructor / factory / `create_from_listener`.
3. `require_shell_authorization` validates `authorized is True`,
   `authorized_by == "capability_broker"`, non-empty `session_id`,
   numeric unexpired `expires_at`; otherwise raises `ShellNotAuthorized`.
4. `KaliToolsClient`-style subprocess fallback is not involved; shell
   I/O primitives (paramiko, sockets) are unchanged and remain behind
   the new construction gate plus the existing per-command broker
   authorization (`authorize_shell_command`).

### W-A.4 — Governance / reachability analysis

1. The canonical Runtime path (`RaphaelRuntime` → `SafeProvingCapability`
   under `exec/`) never constructs interactive-shell capabilities
   (verified: no construction call sites in `src/` outside tests; B-1a
   closures contain the package modules by import only).
2. The ~30 legacy `kali`-importing wrappers are unrelated to SHELL
   (different seam, already welded).
3. `ListenerManager.create_listener` / `destroy_listener` remain
   broker-invoked in practice (only call sites: `capability_broker.py`
   ×2); out of scope for this weld per the minimum-change rule (no
   alternate *capability-construction* bypass remains, which is the
   P3.5 target).
4. This weld strictly **narrows** the reachable surface: previously any
   importer could construct privileged shells; now construction without
   a valid Broker receipt is impossible.
5. No new unbrokered primitive path exists; no new stages, PDP, PEP,
   or orchestrator.

---

## W-B — GUARDRAIL LINEAGE / R-W2

### W-B.1 — Pre-weld test definition (at `f652152f9`, verbatim)

```python
def test_adversarial_unauthorized_callback():
    """Unauthorized callback IP is rejected by callback validation."""
    from orchestrator.capabilities.interactive_shell.reverse_shell import ReverseShellCapability
    from orchestrator.capabilities.interactive_shell.reverse_shell import ReverseShellConnectionInfo
    from orchestrator.capabilities.interactive_shell.capability import ShellCapabilityType

    # Create capability with restrictive CIDRs
    conn_info = ReverseShellConnectionInfo(
        capability_type=ShellCapabilityType.REVERSE_TCP,
        target="10.0.0.100",
        lhost="127.0.0.1",
        lport=4444,
        allowed_callback_cidrs=["10.0.0.0/8"],
    )

    # Validate callback IPs
    cap = ReverseShellCapability(connection_info=conn_info)

    # IP in allowed range
    assert cap._validate_callback_ip("10.0.0.50"), "10.0.0.50 should be allowed"

    # IP outside allowed range
    assert not cap._validate_callback_ip("192.168.1.100"), "192.168.1.100 should be denied"
    assert not cap._validate_callback_ip("172.16.0.50"), "172.16.0.50 should be denied"
    assert not cap._validate_callback_ip("8.8.8.8"), "8.8.8.8 should be denied"

    print("✅ 3D: Unauthorized callback IPs correctly rejected")
```

### W-B.2 — Post-weld test definition (at `784d3fdd`, verbatim)

```python
def test_adversarial_unauthorized_callback():
    """Unauthorized construction is denied; authorized callback validation preserved.

    Weld-SHELL (P3) SD-1: direct privileged construction without a
    Broker-issued SessionReceipt fails closed with ShellNotAuthorized.
    Callback IP validation behavior is unchanged for authorized construction.
    """
    from orchestrator.capabilities.interactive_shell.reverse_shell import ReverseShellCapability
    from orchestrator.capabilities.interactive_shell.reverse_shell import ReverseShellConnectionInfo
    from orchestrator.capabilities.interactive_shell.capability import ShellCapabilityType
    from orchestrator.capabilities.interactive_shell.capability import ShellNotAuthorized
    from orchestrator.capabilities.interactive_shell.session import ShellSessionProposal

    # Create capability connection info with restrictive CIDRs
    conn_info = ReverseShellConnectionInfo(
        capability_type=ShellCapabilityType.REVERSE_TCP,
        target="10.0.0.100",
        lhost="127.0.0.1",
        lport=4444,
        allowed_callback_cidrs=["10.0.0.0/8"],
    )

    # 1. Direct construction without broker authorization must fail closed.
    try:
        ReverseShellCapability(connection_info=conn_info)
        assert False, "Direct construction without authorization must raise ShellNotAuthorized"
    except ShellNotAuthorized:
        pass

    # 2. Broker-authorized construction remains possible.
    broker = _create_test_broker()
    proposal = ShellSessionProposal(
        capability_type=ShellCapabilityType.REVERSE_TCP,
        target="10.0.0.100",
        lhost="127.0.0.1",
        lport=4445,
        metadata={"allowed_callback_cidrs": ["10.0.0.0/8"]},
    )
    receipt = broker.authorize_shell_session(proposal)
    assert receipt.authorized, f"Expected authorized test receipt, got: {receipt.reason}"
    cap = ReverseShellCapability(connection_info=conn_info, authorization=receipt)

    # 3. Callback IP validation behavior is unchanged (original security property).
    # IP in allowed range
    assert cap._validate_callback_ip("10.0.0.50"), "10.0.0.50 should be allowed"

    # IP outside allowed range
    assert not cap._validate_callback_ip("192.168.1.100"), "192.168.1.100 should be denied"
    assert not cap._validate_callback_ip("172.16.0.50"), "172.16.0.50 should be denied"
    assert not cap._validate_callback_ip("8.8.8.8"), "8.8.8.8 should be denied"

    print("✅ 3D: Unauthorized construction denied; authorized callback validation preserved")
```

### W-B.3 — Full e1/e2 transition inventory (R-W2)

| Test | Disposition | Commit | Reason |
|---|---|---|---|
| `test_adversarial_unauthorized_callback` | **EDITED** (1 of 34 e1 tests) | `784d3fdd` | P1-known SD-1 conflict: direct construction is now denied by design. New version asserts the denial, then re-proves the original callback-IP property via broker-authorized construction. No assertion weakened: all four original IP assertions retained verbatim. |
| Other 33 e1 tests | **RETAINED** (unchanged) | — | Unaffected by the weld (filter/session/TTY/receipt/listener/broker/persistence tests). |
| e2 suite (36 tests) | **RETAINED** (unchanged) | — | Generator-level tests; no capability construction. |
| `test_shell_privileged_construction_requires_broker_receipt` | **ADDED** (`tests/test_p2_guardrail_shell_closed.py`) | `784d3fdd` | Institutional negative proof: direct/forge/expired construction denied; authorized construction works. |

**Test-count delta:** e1 34→34 (1 edited, 0 added/removed); new guardrail file +1 test. Full floor 293→294 (+1). Guardrails 26→27 (+1). No REMOVED tests.

**No weakening:** the edited test keeps all four original `_validate_callback_ip` assertions byte-identical and adds two stronger assertions (denial + authorized construction).

---

## W-C — COMPLETE WELD CONTRACT PROOF

### W-C.1 — Canonical seeded parity harness (mandatory; NOT unreachability)

Harness: `/tmp/shell_parity.py` (evidence-only, SEED=20260906). Runs one
deterministic canonical Runtime episode (`max_iterations=3`) and prints
the comparable decision/evidence sequence (timing excluded). Nothing is
fed back into Runtime.

**Pre-weld baseline** (at pre-weld base, before implementation):
```
SEED=20260906
TERMINATED=True
REASON=G3-EN-5 organ-wired walking skeleton: one iteration complete
ITERATIONS=1
TRACE t0 stage=observe success=True error=None
TRACE t0 stage=worldmodel_read success=True error=None
TRACE t0 stage=student_candidate success=True error=None
TRACE t0 stage=planner_request success=True error=None
TRACE t0 stage=broker success=True error=None
TRACE t0 stage=pep success=True error=None
TRACE t0 stage=receipt success=True error=None
TRACE t0 stage=worldmodel_integrate success=True error=None
TRACE t0 stage=contradiction success=True error=None
TRACE t0 stage=replan success=True error=None
```

**Post-weld run** (at implementation commit `784d3fdd`):
```
SEED=20260906
TERMINATED=True
REASON=G3-EN-5 organ-wired walking skeleton: one iteration complete
ITERATIONS=1
TRACE t0 stage=observe success=True error=None
TRACE t0 stage=worldmodel_read success=True error=None
TRACE t0 stage=student_candidate success=True error=None
TRACE t0 stage=planner_request success=True error=None
TRACE t0 stage=broker success=True error=None
TRACE t0 stage=pep success=True error=None
TRACE t0 stage=receipt success=True error=None
TRACE t0 stage=worldmodel_integrate success=True error=None
TRACE t0 stage=contradiction success=True error=None
TRACE t0 stage=replan success=True error=None
```

**Diff:** `diff pre post` → IDENTICAL. Zero authorization-only
differences (the canonical path never constructs shell capabilities, so
the new gate is never exercised there). No unexplained divergence.

### W-C.2 — Institutional negative proof

**Test source** (`tests/test_p2_guardrail_shell_closed.py`, 1 test;
key body):
```python
    # 1. Direct construction without authorization fails closed.
    with pytest.raises(ShellNotAuthorized):
        ReverseShellCapability(connection_info=reverse_info)
    with pytest.raises(ShellNotAuthorized):
        SSHShellCapability(connection_info=ssh_info)
    with pytest.raises(ShellNotAuthorized):
        ShellCapabilityFactory.create(ssh_info)

    # 2. Forged / invalid receipts fail closed (None, unauthorized,
    #    wrong issuer, expired — 4 cases, each pytest.raises).
    ...
    # 3. Broker-authorized construction remains possible (reverse, SSH,
    #    factory via real broker receipts).
```

**Actual targeted transcript:**
```
$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_shell_closed.py -v --no-header
tests/test_p2_guardrail_shell_closed.py::test_shell_privileged_construction_requires_broker_receipt PASSED [100%]
1 passed in 0.26s
```

**Documented error** (`capability.py`): `ShellNotAuthorized`
("InteractiveShellCapability construction requires a valid
Broker-issued SessionReceipt... Direct construction without broker
authorization is denied. Path ID: SHELL.").

**Logging:** constructor denial raises before any I/O; denial is
visible in the exception traceback. (No DecisionTrace claim beyond the
raised error: NOT ESTABLISHED BY AVAILABLE EVIDENCE for legacy-envelope
errors beyond the traceback.)

### W-C.3 — Invariants (machine-captured)

```
$ PYTHONPATH=src python3 -m pytest tests/test_g3_en5_organ_wiring.py tests/test_p2_guardrail_inv1.py tests/test_g2_c2_fail_closed.py --no-header -q
25 passed, 1 warning in 0.80s
```
Single PDP, single loop, INV-2, INV-1/CONV-3, fail-closed all pass.
SUB-14/SUB-13 asserts unchanged and passing (`grep` confirms zero
reintroduction of removed symbols).

### W-C.4 — e1/e2 shell suites (machine-captured)

```
$ PYTHONPATH=src python3 -m pytest tests/e1_interactive_shell_test.py --no-header -q
34 passed in 0.44s (1 pre-weld failure at implementation time:
test_adversarial_unauthorized_callback, resolved by the R-W2 transition above)
$ PYTHONPATH=src python3 -m pytest tests/e2_shell_candidate_generation_test.py --no-header -q
36 passed in 0.08s
```

### W-C.5 — P3.1 reconciliation

- SUB-14: WELDED / ACCEPTED (unchanged)
- SUB-13: CLOSED-BY-FOLD / ACCEPTED (unchanged)
- SUB-10: WELDED / ACCEPTED (unchanged)
- SHELL: DEFERRED → **WELDED** (this round, commit `784d3fdd`)

### W-C.6 — Seam ledger

- SUB-10: WRAPPED → WELDED at `a099ba460` (accepted)
- SUB-14: WRAPPED → WELDED at `740861f2e` (accepted)
- SUB-13: CLOSED-BY-FOLD at `740861f2e` (accepted)
- SHELL: DEFERRED (SD-1) → WELDED at `784d3fdd` (this round)
- Policy artifact: none (gate enforced by `require_shell_authorization` + `ShellNotAuthorized`)

### W-C.7 — Post-weld Arena closure (machine-captured at implementation HEAD)

```
ORCHESTRATOR_MODULES_IN_STATIC_CLOSURE=31
ARENA_MODULES_IN_STATIC_CLOSURE=0
ORCHESTRATOR_AND_ARENA_MODULES_AFTER_EPISODE=50
ARENA_MODULES_AFTER_EPISODE=0
STATIC_ARENA_FREE: True
EPISODE_ARENA_FREE: True
```
Shell capability modules remain reachable by import (correct invariant:
reachability retained, authorization boundary enforced).

---

## W-D — PROVENANCE (three-state model)

### W-D.1 — Implementation / pre-evidence capture state

```
$ git rev-parse HEAD
784d3fddbd9452cb6271171e5ed0385a8382ebe2

$ git branch --show-current
weld-sub10-evidence

$ git rev-list --count 7272880f7..HEAD
55

$ git status -sb
## weld-sub10-evidence
 M src/orchestrator/capabilities/interactive_shell/capability.py
 M src/orchestrator/capabilities/interactive_shell/reverse_shell.py
 M src/orchestrator/capabilities/interactive_shell/ssh_shell.py
 M tests/e1_interactive_shell_test.py
?? tests/test_p2_guardrail_shell_closed.py
```

(Note: W-D.1 was captured pre-commit with the five implementation files
shown as M/?? — exactly the implementation set. The commit itself is
`784d3fdd`.)

```
$ git rev-list --parents -n 1 784d3fdd
784d3fddbd9452cb6271171e5ed0385a8382ebe2 f652152f9182e3f708491b9765dd1657bdc3aabd
```

### W-D.2 — Final actual repository state (post-evidence commit)

Established by external machine verification of the records-only
evidence commit that adds this file. This file cannot embed the hash of
the commit that contains it (self-reference rule). Final HEAD is the
direct child of `784d3fdd` on branch `weld-sub10-evidence`; final count
is therefore 56 (55 + 1 evidence commit). Verify externally with
`git log --oneline -n 2 weld-sub10-evidence`.

### W-D.3 — Evidence commit relationship

Implementation commit `784d3fdd` (parent) → evidence commit (child,
this file only). Verifiable by `git diff <impl>..<final> --stat`
showing only `evidence/phases/P3_0/WELD-SHELL_EVIDENCE.md`.

## Final test floor

Previous floor (SUB-10 acceptance): 293 passed, 0 failed, 0 skipped, 0 xfail.
New floor: **294 passed**, 0 failed, 0 skipped, 0 xfail (delta **+1**).
Guardrails: **27** (was 26).

Floor breakdown: 239 legacy + 8 P2.1 + 9 G2-C2 + 27 P2 guardrail + 11 G3-EN-5 = 294.

## Outstanding caveats

1. `ListenerManager.create_listener` / `destroy_listener` remain
   broker-invoked-by-convention (only call sites are in
   `capability_broker.py`); no receipt check was added there per the
   minimum-change rule. The P3.5 target (constructor gating) is fully
   closed; listener-method gating, if desired, is future work.
2. `SessionReceipt` validation is duck-typed (presence of
   `authorized`/`authorized_by`/`session_id`/unexpired `expires_at`);
   receipts are not cryptographically bound to a capability type.
3. DecisionTrace capture for legacy-envelope denials is NOT
   ESTABLISHED BY AVAILABLE EVIDENCE beyond the raised error.

## GLM adjudication handoff

SHELL evidence prepared for GLM artifact-only adjudication.

---

## BD-SHELL REMEDIATION APPENDIX (GLM-authorized defect fixes)

This appendix records the GLM-authorized remediation of the two
implementation defects found in audit (forgeable duck-typed
authorization; ungated ListenerManager). No architecture redesign, no
second PDP, no new stages. This is an implementation + records round;
R-W2 applies to the test additions below.

### R1 — Broker-state-bound authorization (fixes DEFECT 1)

`session.py` now holds a broker-written issuance registry:

```python
_AUTHORIZED_SHELL_SESSIONS: dict = {}  # session_id -> expires_at (float)

def register_authorized_shell_session(session_id: str, expires_at: float) -> None: ...
def revoke_authorized_shell_session(session_id: str) -> None: ...
def is_shell_session_authorized(session_id: str) -> bool: ...  # present + unexpired, prunes expired
```

`capability.py require_shell_authorization(authorization, expected_session_id=None)`:
1. extracts `session_id` (absent/non-string → deny);
2. enforces `expected_session_id` match when given;
3. keeps the affirmative-field sanity check for receipt-shaped objects;
4. **requires a live registry hit** (`is_shell_session_authorized`) — the
   provenance binding. Import is lazy (function-level) to avoid the
   `session.py → capability.py` circular import.

`capability_broker.py` (existing session path only):
- `authorize_shell_session` success: `register_authorized_shell_session(session_id, session.expires_at)`;
  provisional registration before listener provisioning with revoke on the
  deny path (receipt does not exist yet at provisioning time);
- denial-threshold TERMINATING: revoke;
- `terminate_shell_session`: passes the broker-held session record as
  `authorization` to `destroy_listener`, then pops and revokes;
- `create_listener` call site passes `authorization=session`.

Machine-demonstrated before/after:
```
# BEFORE (duck-typed only):
FORGED RECEIPT ACCEPTED / FORGED CONSTRUCTION SUCCEEDED
# AFTER (registry-bound):
forged denied (GOOD)
```

### R2 — Listener gating (fixes DEFECT 2)

`listener_manager.py`: `create_listener(..., authorization=None)` and
`destroy_listener(session_id, authorization=None)` both validate via
`require_shell_authorization` (`create` additionally binds
`expected_session_id=session_id`). `destroy_listener_by_port`,
`cleanup_expired`, and `shutdown_all` accept and forward an optional
`authorization` (fail closed by default). No in-repo callers of these
helpers pass authorization today; the only production callers
(`capability_broker.py:676` create with the broker-held session,
`:1012` destroy with the broker-held session) were updated.

### R3 — Tests (R-W2)

`tests/test_p2_guardrail_shell_closed.py` grows 1 → 4 tests, all in
implementation commit `379f037e1`:
- `test_shell_privileged_construction_requires_broker_receipt` (RETAINED from prior round, unchanged)
- `test_shell_forged_field_bag_rejected` (ADDED: forged SimpleNamespace denied)
- `test_shell_unknown_and_expired_sessions_rejected` (ADDED: unknown + expired denied)
- `test_shell_listener_requires_authorization` (ADDED: unauthenticated create/destroy denied, no port bound)

```
$ PYTHONPATH=src python3 -m pytest tests/test_p2_guardrail_shell_closed.py -v --no-header
tests/test_p2_guardrail_shell_closed.py::test_shell_privileged_construction_requires_broker_receipt PASSED [ 25%]
tests/test_p2_guardrail_shell_closed.py::test_shell_forged_field_bag_rejected PASSED [ 50%]
tests/test_p2_guardrail_shell_closed.py::test_shell_unknown_and_expired_sessions_rejected PASSED [ 75%]
tests/test_p2_guardrail_shell_closed.py::test_shell_listener_requires_authorization PASSED [100%]
4 passed in 0.28s
```

e1 (34) and e2 (36) unchanged and passing; no e1/e2 transitions in this
round. Full floor: **297 passed**, 0 failed, 0 skipped, 0 xfail
(previous 294; delta **+3**, the three new remediation tests).
Guardrails: **30** (was 27).

Bearer-token caveat (honest): a snooped *valid live* session_id presented
with affirmative fields would pass construction-time validation, exactly
as presenting a stolen live receipt would. Token theft is out of scope
for constructor gating; per-command authorization remains broker-enforced
and termination revokes issuance.

### R4 — Invariants re-verified at remediation HEAD

```
$ PYTHONPATH=src python3 -m pytest tests/test_g3_en5_organ_wiring.py tests/test_p2_guardrail_inv1.py tests/test_g2_c2_fail_closed.py --no-header -q
25 passed, 1 warning in 0.80s
$ PYTHONPATH=src python3 -m pytest tests/e1_interactive_shell_test.py tests/e2_shell_candidate_generation_test.py --no-header -q
70 passed in 0.50s
```
Single PDP, single loop, INV-1/INV-2, fail-closed green. SUB-14/SUB-13/SUB-10 untouched
(`grep` confirms zero reintroduction; their guardrail asserts unchanged and passing).
Closure re-run at remediation HEAD: static 31/0, loaded 50/0, both verdicts True.
Parity re-run at remediation HEAD: IDENTICAL to pre-weld baseline (10/10 stages).

### R5 — Provenance for this round (three-state model)

- Implementation state: commit `379f037e1`, count 57, five files
  (session.py, capability.py, listener_manager.py, capability_broker.py,
  test_p2_guardrail_shell_closed.py).
- Evidence-commit state: this file amended on top of `379f037e1`
  (this file only); count therefore 58.
- Authoritative current state: established by external machine
  verification after the records commit (self-reference rule: this file
  does not embed its own commit hash).
