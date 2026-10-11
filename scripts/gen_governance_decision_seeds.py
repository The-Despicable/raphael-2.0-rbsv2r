#!/usr/bin/env python3
"""gen_governance_decision_seeds.py — emit the open operator decisions as PROPOSED.

Six G8-scope seeds transcribed from the 2026-10-09 blocker report, plus five
architecture-adjudication proposals (GD-2026-10-11-01..05) registered by the
delegated adjudication commissioned on 2026-10-11. Both groups are PROPOSED
records and carry no authority.

Why this script exists
----------------------
The seeds in ``evidence/GOVERNANCE_DECISIONS_20261009.jsonl`` carry a
``content_hash`` over their canonical content. Hand-typing those hashes is
exactly the kind of unverifiable artifact this remediation is trying to reduce,
so the seed file is *generated* from source-quoted content instead.

What it will NOT do
-------------------
* It writes **PROPOSED** records only. There is no branch, flag, or argument
  here that can emit ADOPTED/REJECTED. Ratification is an operator act and must
  go through the registry's authority rules, not through this generator.
* It never fills ``authority_principal`` or ``decided_at``. Those stay empty
  strings, which is what makes the records proposals.
* It does not choose an outcome. ``decision_text`` records that no decision has
  been taken.
* Since the ledger acquired decision history, it **refuses to overwrite a
  ledger holding records it did not generate**. Rewriting from the eleven seeds
  would delete every appended ruling, retraction, or rejection. A generator that
  can silently destroy decision history is the opposite of the point of
  generating those records from source in the first place.

Overwrite guard
---------------
Added after the independent audit of ``36329f0ab`` found that re-running this
script would truncate the ledger from 15 records to 11 and delete four decision
events.

``main()`` inspects ``OUT_PATH`` **before** writing and refuses when the
existing file holds anything beyond unratified proposals. Each line is parsed
with plain ``json`` rather than :class:`GovernanceRegistry`, deliberately: a
ledger holding delegated rulings does not import without a delegation set, and
this guard must work in precisely the case where someone is about to destroy
such a ledger. **Malformed or unreadable existing data causes refusal, never
overwrite** — ambiguity is a reason to stop, not a reason to proceed.

Exit status: ``0`` written or already up to date; ``2`` refused, file untouched.

Regenerate with::

    PYTHONPATH=src .venv/bin/python scripts/gen_governance_decision_seeds.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from orchestrator.rsi.governance_registry import (  # noqa: E402
    STATUS_PROPOSED,
    GovernanceRegistry,
    OperatorDecisionRecord,
)

#: Any status other than PROPOSED represents a decision event this generator
#: cannot reproduce. Listed explicitly so that adding a new status to the
#: registry does not silently become writable-over.
NON_PROPOSAL_STATUSES = ("ADOPTED", "REJECTED", "SUPERSEDED", "INVALIDATED")

OUT_PATH = REPO_ROOT / "evidence" / "GOVERNANCE_DECISIONS_20261009.jsonl"

SOURCE_BRIEF = (
    "reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md#5 item 4"
)
PROPOSER = (
    "G3 remediation task (engineering); proposals transcribed from "
    "RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md section 5 item 4"
)
NO_DECISION = (
    "NO DECISION TAKEN. This record exists so the open decision is explicit and "
    "auditable. It carries no authority and confers none. Ratification requires "
    "a named authority principal distinct from the proposer, supplied at "
    "ratification time and recorded verbatim."
)

# Each option is quoted or closely paraphrased from the cited source. The option
# set is a TRANSCRIPTION of what the source shows, not an engineering proposal
# of new options. Confirming or extending the option set is itself an operator
# decision.
SEEDS = (
    dict(
        decision_id="GD-2026-10-09-01",
        topic="holdout-provenance-recovery",
        question=(
            "Authorize provenance recovery attempts for the canonical RBS-v4 "
            "holdout dataset from outside this repository, or formally accept "
            "it as permanently unverifiable?"
        ),
        allowed_options=(
            "authorize provenance recovery outside this repository",
            "formally accept permanent UNVERIFIABLE classification",
        ),
        affected_gate="G8",
        decision_text=NO_DECISION,
        evidence_refs=(
            "evaluations/campaign/HOLDOUT_CLASSIFICATION_20261009.json",
            "reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md",
        ),
    ),
    dict(
        decision_id="GD-2026-10-09-02",
        topic="policy-identity-mode",
        question=(
            "Must adopted production evaluation configurations set "
            "require_policy_identity=True, i.e. is the derive-and-verify mode "
            "mandatory rather than optional?"
        ),
        allowed_options=(
            "derive-and-verify mandatory in adopted configs (require_policy_identity=True)",
            "leave require_policy_identity at its current default of False",
        ),
        affected_gate="G8",
        decision_text=NO_DECISION,
        evidence_refs=(
            "src/orchestrator/rsi/evaluation_gate.py",
            "reports/POLICY_IDENTITY_REDERIVATION_AND_RESIDUALS_2026-10-09.md",
            "reports/POLICY_MANIFEST_AUTHORITY_2026-10-09.md",
        ),
    ),
    dict(
        decision_id="GD-2026-10-09-03",
        topic="denominator-and-exclusion-semantics",
        question=(
            "Which denominators and exclusion rules are admissible in reported "
            "evaluation aggregates, given that no success-rate denominator has "
            "been adopted?"
        ),
        allowed_options=(
            "per-arm outcome-category counts only; any caller-computed rate is "
            "labelled an unadopted denominator",
            "adopt an explicit rate denominator",
        ),
        affected_gate="G8",
        decision_text=NO_DECISION,
        evidence_refs=("src/orchestrator/rsi/measurement_contract.py",),
    ),
    dict(
        decision_id="GD-2026-10-09-04",
        topic="configuration-adoption-authority",
        question=(
            "Who may create an ADOPTED entry in the evaluation-configuration "
            "adoption registry, and what evidence must accompany it?"
        ),
        allowed_options=(),  # filled below; source states the question, not the options
        affected_gate="G8",
        decision_text=NO_DECISION,
        evidence_refs=(
            "reports/RAPHAEL_BLOCKER_RESOLUTION_REPORT_2026-10-09.md",
            "src/orchestrator/rsi/evaluation_gate.py",
        ),
    ),
    dict(
        decision_id="GD-2026-10-09-05",
        topic="statistical-policy",
        question=(
            "What statistical policy (significance level, multiplicity handling, "
            "minimum sample, uncertainty reporting) governs promotion claims?"
        ),
        allowed_options=(),  # source records the question only; no options defined
        affected_gate="G8",
        decision_text=NO_DECISION,
        evidence_refs=("docs/EvaluationProtocol.md",),
    ),
    dict(
        decision_id="GD-2026-10-09-06",
        topic="snapshot-and-replay-semantics",
        question=(
            "What do the snapshot/replay labels SAME, CROSS and UNVERIFIABLE "
            "mean, and when does each apply?"
        ),
        allowed_options=(),  # labels deliberately unimplemented pending this ruling
        affected_gate="G8",
        decision_text=NO_DECISION,
        evidence_refs=("src/orchestrator/rsi/snapshot.py",),
    ),
)

# ── Architecture-adjudication proposals (2026-10-11) ────────────────────────
# Registered from the delegated adjudication commissioned by the operator on
# 2026-10-11. Unlike the six G8 seeds (which record open questions with no
# outcome), these carry a proposed outcome. They remain PROPOSED records:
# authority_principal and decided_at are never filled here, and ratification
# must go through the registry's authority rules (named principal distinct
# from the proposer). GD-2026-10-11-01 (retain/retire component) and
# GD-2026-10-11-03 (legacy weld-perimeter component) additionally require GLM
# architecture-authority concurrence — see each decision_text.

ADJ_PROPOSER = (
    "Delegated Architecture Adjudicator (operator-commissioned agent session, "
    "2026-10-11)"
)

ADJ_SOURCE = (
    "Operator commission session 2026-10-11; delegated adjudication performed "
    "against audit baseline commit fc3e2c132591eab7edaa12e97e13fe2d01619411 / "
    "tree e24d42bf7f7655293f3eb3a273c9ce4d94b1e061. No repository report file "
    "exists for this adjudication; the rationale and evidence are preserved in "
    "this record's decision_text and evidence_refs."
)

PROVISIONAL = (
    "PROPOSED OUTCOME (PROVISIONAL). Carries no authority and confers none; "
    "effective only if ratified in this ledger by a named authority principal "
    "distinct from the proposer, recorded verbatim. "
)

ADJUDICATION_SEEDS = (
    dict(
        decision_id="GD-2026-10-11-01",
        topic="bridge-disposition",
        question=(
            "What is the authorized disposition of the OpenCode JSON-RPC "
            "bridge (src/bridge/raphael_bridge.py): retain as a supported "
            "interface, quarantine, retire, or an alternative?"
        ),
        allowed_options=(
            "B1 RETAIN: supported product interface with a defined authorization contract",
            "B2 QUARANTINE: outside authorized operational use pending an approved disposition and authorization contract",
            "B3 RETIRE: designated obsolete or unsupported",
            "B4 ALTERNATIVE: another specific disposition with rationale and scope",
        ),
        affected_gate="G3",
        decision_text=PROVISIONAL + (
            "PROPOSED B2 — QUARANTINE. The bridge remains outside authorized "
            "operational use until an approved disposition and authorization "
            "contract exist. ESTABLISHED FACTS (verified at audit baseline "
            "fc3e2c132/e24d42bf): a live TypeScript consumer launches the "
            "bridge (src/cli/src/services/raphael-bridge.ts:32-49; "
            "src/cli/src/tools/raphaelTools.ts:2-6; src/cli/package.json "
            "raphael:bridge recipe); the bridge and both config shims insert "
            "an absent directory at sys.path[0] (/home/yaser/raphael-2.0, "
            "verified absent) at raphael_bridge.py:15, config/paths.py:2, "
            "config/target.py:2; the four agent.* routes dispatch to "
            "module-level handle() functions that do not exist in the agent "
            "modules (dead-end routes); 25 weld-table methods are gated "
            "fail-closed via enforce_broker_mediation and DENY under "
            "bootstrap-v0 on action-type, literal capability membership, and "
            "impact; non-weld effect-bearing methods (persona.set, target.set, "
            "scope.set, brain.memory_store/recall, conductor.call/"
            "select_strategy) carry no bridge-level authorization contract. "
            "Runtime startup, importability, and deployment status remain "
            "UNVERIFIED (execution was prohibited by the commissioning "
            "orders; a launch recipe is not proof of operation and a broken "
            "path is not proof of intended retirement). REJECTED: B1 (no "
            "authorization contract exists to support a supported-interface "
            "claim); B3 (no record designates retirement intent; the CLI "
            "consumer is live source). DEPENDENCIES: this disposition "
            "precedes any bridge repair, retirement, or authorization-"
            "contract design. Any future contract must define six "
            "authorization classes — configuration/process-state mutation; "
            "target/scope mutation; persistent data and memory operations; "
            "external model/API invocation; execution-capable dispatch; and "
            "the four agent.* routes — all routed through the canonical "
            "Broker (ADR-003); no second authorization authority. "
            "RATIFICATION: the quarantine and the contract contents are "
            "operator-ratifiable; any retain/retire disposition or second "
            "enforcement surface additionally requires GLM architecture "
            "authority (ADR-006 INV-5 single-entry doctrine). ENGINEERING: "
            "disposition and contract design records only; no implementation "
            "authorized."
        ),
        evidence_refs=(
            "src/bridge/raphael_bridge.py",
            "src/cli/src/services/raphael-bridge.ts",
            "src/cli/src/tools/raphaelTools.ts",
            "src/cli/package.json",
            "src/orchestrator/config/paths.py",
            "src/orchestrator/config/target.py",
            "docs/adr/ADR-003-broker-pdp-pep-separation.md",
            "docs/adr/ADR-006-no-second-cognitive-entry-point.md",
            "evidence/phases/P3_0_reinventory/WELD_SET.md",
            "policies/bootstrap-v0.json",
        ),
        proposer=ADJ_PROPOSER,
        source_ref=ADJ_SOURCE,
    ),
    dict(
        decision_id="GD-2026-10-11-02",
        topic="postex-agent-path-boundary",
        question=(
            "Does the W-14 weld on src/orchestrator/postex/pipeline.py cover "
            "the separate src/orchestrator/agents/postex.py execution path, "
            "and what is that path's authorized status?"
        ),
        allowed_options=(
            "P1 PIPELINE ONLY: W-14 covers the pipeline; the agent path requires its own separate ruling",
            "P2 BOTH PATHS: W-14 was intended to cover both, but implementation does not demonstrate it",
            "P3 QUARANTINE: the separate PostEx agent path is outside authorized use",
            "P4 ALTERNATIVE: another precise scope",
        ),
        affected_gate="G3",
        decision_text=PROVISIONAL + (
            "PROPOSED P3 — QUARANTINE the separate PostEx agent path. "
            "src/orchestrator/agents/postex.py is outside authorized use "
            "until it is either welded through the canonical Broker or "
            "deprecated/deleted. ESTABLISHED FACTS (audit baseline "
            "fc3e2c132/e24d42bf): the pipeline entry "
            "src/orchestrator/postex/pipeline.py:39-48 carries the weld gate "
            "(enforce_broker_mediation, capability=postex.pipeline, "
            "path_id=R3.0-P23, weld_ticket=W-14); WELD_SET.md's authoritative "
            "W-14 scope is R3.0-P23 standalone service entries — a W-14 "
            "ticket at one entry is NOT coverage of all post-execution paths. "
            "The separate agent module has no Broker mediation anywhere; its "
            "only control is _check_hitl imported from agents/exploit.py:110-121, "
            "which RAPHAEL_HITL_BYPASS disables (see GD-2026-10-11-04), and "
            "it directly drives NetExecWrapper, WinRMExploit, "
            "BloodHoundIntegration, LadonScanner, and PupyC2 (agents/postex.py:"
            "103-187). Sibling agents are weld-gated (agents/exploit.py:440, "
            "W-10; agents/engage.py:53-62, W-03); the PostEx agent is the "
            "outlier. The two PostEx modules do not import each other. "
            "REJECTED: P1 (defers a decidable question the evidence already "
            "answers); P2 (asserts an intent that no record documents). NOTE: "
            "WELDED in WELD_SET.md is an engineering claim, not a gate "
            "acceptance; G3 remains NOT ACCEPTED. DEPENDENCIES: precedes "
            "authorization remediation design for the agent path and its "
            "wrappers (weld-or-deprecate per ADR-006/P9). An AUTHORIZED "
            "receipt at any entry gate authorizes nothing downstream without "
            "receipt-to-execution binding (see GD-2026-10-11-03). "
            "RATIFICATION: operator. ENGINEERING: remediation design records "
            "only; implementation not authorized."
        ),
        evidence_refs=(
            "src/orchestrator/postex/pipeline.py",
            "src/orchestrator/agents/postex.py",
            "src/orchestrator/agents/exploit.py",
            "src/orchestrator/agents/engage.py",
            "src/orchestrator/auth.py",
            "evidence/phases/P3_0_reinventory/WELD_SET.md",
            "docs/adr/ADR-003-broker-pdp-pep-separation.md",
            "docs/adr/ADR-004-born-gated-runtime.md",
        ),
        proposer=ADJ_PROPOSER,
        source_ref=ADJ_SOURCE,
    ),
    dict(
        decision_id="GD-2026-10-11-03",
        topic="receipt-to-execution-binding",
        question=(
            "Must an authorization receipt be bound to the particular "
            "operation subsequently executed (target, capability, method and "
            "arguments, execution identity, terminal outcome, evidence "
            "linkage), and at which perimeters?"
        ),
        allowed_options=(
            "R1 MANDATORY BINDING: authorization must be bound to the exact operation subsequently executed",
            "R2 BOUNDED ENTRY-POINT AUTHORIZATION: entry-point-only authorization for explicitly defined call-site classes, with remaining controls specified",
            "R3 RESERVED AUTHORITY: the decision is reserved to a specifically identified authority",
            "R4 ALTERNATIVE: another precise outcome",
        ),
        affected_gate="G3/G4 (INV-2, INV-3)",
        decision_text=PROVISIONAL + (
            "PROPOSED R1 — MANDATORY receipt-to-execution binding, in two "
            "components with different authority requirements. (1) CANONICAL "
            "RUNTIME — APPLICATION of accepted requirements: ADR-003 INV-2 "
            "(every execution event carries the Broker decision_id) and "
            "INV-3 (execution-derived claims require receipts), already "
            "implemented and tested as the section-14.6 F1 six-dimension "
            "binding: src/orchestrator/hardening/action_receipt.py "
            "hash-binds target, capability, method, impact, action_type and "
            "authorized_argv and tracks STARTED to SUCCEEDED/FAILED/TIMEOUT "
            "with evidence_ids; src/orchestrator/runtime/stages.py binds "
            "receipts to the mission-scoped action id (RSI-1 Fix A) and "
            "persists durable denial records; "
            "evidence/g3_remediation/STATUS.md records F1 as IMPLEMENTED "
            "+ PROVEN. (2) LEGACY WELD PERIMETER — INTERPRETIVE EXTENSION "
            "requiring explicit GLM architecture-authority approval before "
            "or at ratification: all ~57 enforce_broker_mediation call sites "
            "(grep-verified; none captures the return value) discard the "
            "returned receipt, and none demonstrates receipt-to-action "
            "binding. Extending the binding obligation beyond the documented "
            "canonical closure (F2 perimeter record; product-readiness "
            "report section 5.2) is not settled by any accepted record; "
            "operator ratification alone is INSUFFICIENT for this "
            "component. REQUIRED POLICY-LEVEL GUARANTEES: binding of "
            "authorized target; capability; method and arguments; execution "
            "identity/call-site; terminal status; and evidence linkage via "
            "decision_id. EXPLICIT CLARIFICATION: an AUTHORIZED receipt is "
            "an authorization-decision artifact only — it does not "
            "operationally approve any execution, and no weld site "
            "demonstrates that what executed matched what was authorized. "
            "REJECTED: R2 (would institutionalize unbound authorization at "
            "precisely the sites created to close bypasses). DEPENDENCIES: "
            "precedes receipt-lifecycle remediation design; implementation "
            "is additionally barred by the P4/RSI freeze (ReceiptStore is "
            "P4.4 scope). ENGINEERING: design records only; no "
            "implementation authorized."
        ),
        evidence_refs=(
            "src/orchestrator/auth.py",
            "src/orchestrator/brain/capability_broker.py",
            "src/orchestrator/hardening/action_receipt.py",
            "src/orchestrator/runtime/stages.py",
            "src/orchestrator/exec/receipt_store.py",
            "src/orchestrator/exec/evidence_store.py",
            "evidence/g3_remediation/STATUS.md",
            "docs/adr/ADR-003-broker-pdp-pep-separation.md",
            "docs/adr/ADR-012-seam-semantics-ratification.md",
            "reports/product-readiness/RAPHAEL_PRODUCT_READINESS_2026-10-09.md",
        ),
        proposer=ADJ_PROPOSER,
        source_ref=ADJ_SOURCE,
    ),
    dict(
        decision_id="GD-2026-10-11-04",
        topic="hitl-bypass-governance",
        question=(
            "Is the RAPHAEL_HITL_BYPASS environment variable an authorized "
            "operating mode for governed operations?"
        ),
        allowed_options=(
            "H1 PERMITTED: authorized under explicitly stated phases, conditions, safeguards, and audit requirements",
            "H2 PROHIBITED: not permitted under the defined scope",
            "H3 RESERVED AUTHORITY: a specifically identified competent authority must decide",
            "H4 ALTERNATIVE: another precise outcome",
        ),
        affected_gate="NONE (operational safety governance)",
        decision_text=PROVISIONAL + (
            "PROPOSED H2 — PROHIBITED. RAPHAEL_HITL_BYPASS is not an "
            "authorized operating mode in any phase. In any authorized run "
            "the variable must be unset; because the checks use "
            "non-empty-string truthiness, values such as false and 0 "
            "ACTIVATE the bypass, so any non-empty value marks the run "
            "unauthorized and the mechanism cannot be relied on to express "
            "off. ESTABLISHED FACTS (audit baseline fc3e2c132/e24d42bf): "
            "bare truthiness checks at src/orchestrator/agents/"
            "orchestrator.py:20 (_check_hitl_orchestrator, gating "
            "EXPLOIT/POSTEX/LATERAL/EXFIL goals) and src/orchestrator/agents/"
            "exploit.py:112 (_check_hitl, auto-approving every action); "
            "agents/postex.py imports _check_hitl as its ONLY access "
            "control (no Broker gate; see GD-2026-10-11-02). No approval or "
            "risk-acceptance record for the bypass exists in the audited "
            "tree (evidence/governance/ contains only the P4/RSI freeze "
            "notice; this ledger holds no such entry). Implementation "
            "behavior is not authorization. GROUNDS: accepted ADR-004 L8 "
            "(no Runtime-wide OFF mode exists) applied to a legacy-plane "
            "safety bypass; applying L8 beyond the canonical Runtime is an "
            "interpretive step, noted for GLM awareness. SCOPE: the three "
            "reviewed gates (orchestrator goal gate; exploit per-action "
            "gate; postex per-action gate). DEPENDENCIES: governs any "
            "change to or reliance on the bypass; correction design (strict "
            "parsing; Broker-routed) may proceed as records. RATIFICATION: "
            "operator; GLM-awareness note recommended. Any future "
            "permissive mode requires its own explicit approval record with "
            "named principal, phases, conditions, safeguards, and audit "
            "requirements. ENGINEERING: design records only; no "
            "implementation authorized."
        ),
        evidence_refs=(
            "src/orchestrator/agents/orchestrator.py",
            "src/orchestrator/agents/exploit.py",
            "src/orchestrator/agents/postex.py",
            "docs/adr/ADR-004-born-gated-runtime.md",
            "evidence/governance/P4_RSI_FREEZE_NOTICE_20261009.md",
        ),
        proposer=ADJ_PROPOSER,
        source_ref=ADJ_SOURCE,
    ),
    dict(
        decision_id="GD-2026-10-11-05",
        topic="engagement-policy-scope",
        question=(
            "Under what process, if any, may the agents.engage capability "
            "be granted?"
        ),
        allowed_options=(
            "E1 DEFAULT DENY, PERMANENT SCOPE: agents.engage must remain denied under the defined default policy scope",
            "E2 GRANTABLE BY PROCESS: grantable only through a separately authorized policy process with explicit controls",
            "E3 RESERVED AUTHORITY: the policy owner who must decide is specifically identified",
            "E4 ALTERNATIVE: another precise outcome",
        ),
        affected_gate="NONE (engagement authorization process)",
        decision_text=PROVISIONAL + (
            "PROPOSED E2 — GRANTABLE ONLY BY SEPARATELY AUTHORIZED POLICY "
            "PROCESS. agents.engage remains DENIED under the default scope "
            "and under every ACTIVE policy; this record grants no "
            "capability, changes no policy, and does not authorize engaging "
            "any target. Any future grant requires: a named, versioned "
            "policy artifact on the engagement-d1/d2 template (enumerated "
            "allow-lists for action types, capabilities, and targets; "
            "explicit prohibited lists; rate and impact ceilings; "
            "fail-closed loader validation; kill switch) and operator "
            "ratification recorded in this ledger; any grant beyond the "
            "local lab additionally requires the open authorized-use and "
            "legal-posture decision (product-readiness report section "
            "15.7 / SEC-003: no LICENSE, no third-party license inventory, "
            "no offensive-use authorization artifact exists). ESTABLISHED "
            "FACTS (audit baseline fc3e2c132/e24d42bf): "
            "src/orchestrator/agents/engage.py:53-62 proposes "
            "capability=agents.engage, action_type=agent_engage, impact "
            "8.0; the default bootstrap factory "
            "(src/orchestrator/runtime/policy.py make_broker_from_bootstrap "
            "+ policies/bootstrap-v0.json) allows only five read-only "
            "action classes, defaults to deny, and enforces impact ceiling "
            "0.0; broker capability matching is literal membership "
            "(capability_broker.py:241-243), so the asterisk entry is not a "
            "wildcard; engagement-d1-v1.json and engagement-d2-v1.json list "
            "agent_engage in prohibited.action_types; engagement-open-v0.json "
            "is unwired and grants nothing. REJECTED: E1 (records the "
            "default-scope denial but leaves the grant pathway undefined); "
            "E3 (no record assigns engagement-policy ownership to another "
            "principal; the operator is the ratifying owner of record). "
            "DEPENDENCIES: precedes any grant-oriented policy proposal; "
            "external-target activity remains unauthorized regardless of "
            "this record. RATIFICATION: operator. ENGINEERING: none "
            "authorized by this record."
        ),
        evidence_refs=(
            "src/orchestrator/agents/engage.py",
            "src/orchestrator/runtime/policy.py",
            "src/orchestrator/brain/capability_broker.py",
            "policies/bootstrap-v0.json",
            "policies/engagement-d1-v1.json",
            "policies/engagement-d2-v1.json",
            "policies/engagement-open-v0.json",
            "reports/product-readiness/RAPHAEL_PRODUCT_READINESS_2026-10-09.md",
        ),
        proposer=ADJ_PROPOSER,
        source_ref=ADJ_SOURCE,
    ),
)


def build() -> GovernanceRegistry:
    registry = GovernanceRegistry()
    for seed in (*SEEDS, *ADJUDICATION_SEEDS):
        options = seed["allowed_options"]
        if not options:
            # No option set is established by the source records. Record the
            # absence honestly rather than inventing plausible options.
            options = (
                "<no option set established by the source records; "
                "defining the options is part of this decision>",
            )
        record = OperatorDecisionRecord(
            decision_id=seed["decision_id"],
            topic=seed["topic"],
            question=seed["question"],
            allowed_options=tuple(options),
            status=STATUS_PROPOSED,
            proposer=seed.get("proposer", PROPOSER),
            decision_text=seed["decision_text"],
            source_ref=seed.get("source_ref", SOURCE_BRIEF),
            affected_gate=seed["affected_gate"],
            authority_principal="",   # never pre-filled
            decided_at="",            # never pre-filled
            evidence_refs=tuple(seed["evidence_refs"]),
        )
        registry.append(record)
    return registry


def describe_existing_ledger(existing_text: str) -> tuple[str, list[str], list[str]]:
    """Classify the ledger that is about to be overwritten.

    Returns ``(verdict, reasons, blocking_ids)`` where ``verdict`` is one of
    ``"empty"``, ``"refuse"``. Deliberately conservative: anything we cannot
    confidently read as proposals-only is a refusal, never an overwrite.
    """
    reasons: list[str] = []
    blocking: list[str] = []
    lines = [ln for ln in existing_text.splitlines() if ln.strip()]

    for lineno, line in enumerate(lines, start=1):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            return ("refuse", [f"line {lineno} is not valid JSON ({exc})"], [])
        if not isinstance(payload, dict):
            return ("refuse", [f"line {lineno} is not a JSON object"], [])
        status = payload.get("status")
        decision_id = payload.get("decision_id", f"<line {lineno}>")
        if status not in (STATUS_PROPOSED,):
            reasons.append(
                f"{decision_id}: status={status!r} is a decision event this "
                f"generator cannot reproduce")
            blocking.append(str(decision_id))
        # A proposal carrying authority fields is not a plain seed proposal
        # either — it is something a human or a delegation put there.
        if str(payload.get("authority_principal", "")).strip() or \
                str(payload.get("decided_at", "")).strip() or \
                str(payload.get("delegation_ref", "")).strip():
            reasons.append(
                f"{decision_id}: carries authority/delegation fields, so it is "
                f"not an unratified seed proposal")
            blocking.append(str(decision_id))

    return ("refuse" if reasons else "empty", reasons, sorted(set(blocking)))


def main() -> int:
    registry = build()
    text = registry.to_jsonl()

    if registry.authoritative():
        # Unreachable via build(), which is PROPOSED-only, but asserted rather
        # than assumed: the invariant that matters most must not be silent.
        print("ERROR: a PROPOSED seed was treated as authoritative",
              file=sys.stderr)
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    relative = OUT_PATH.relative_to(REPO_ROOT) if OUT_PATH.is_absolute() \
        else OUT_PATH

    if OUT_PATH.exists():
        existing = OUT_PATH.read_text(encoding="utf-8")
        verdict, reasons, blocking = describe_existing_ledger(existing)
        if verdict == "refuse":
            print(f"REFUSING to overwrite {relative}: it holds decision "
                  f"history that this generator did not produce and cannot "
                  f"recreate.", file=sys.stderr)
            for reason in reasons:
                print(f"  - {reason}", file=sys.stderr)
            print(f"  blocking decision ids: {blocking}", file=sys.stderr)
            print("  The file has NOT been modified. Append decisions through "
                  "the registry API under a verified delegation "
                  "(docs/adr/ADR-014); do not regenerate seeds over them.",
                  file=sys.stderr)
            return 2
        if existing == text:
            print(f"{relative} already matches the generated seeds; nothing "
                  "written (no decision history was present)")
            print("authoritative decisions: 0 (expected 0)")
            return 0
        print(f"{relative} holds only unratified seed proposals and differs "
              f"from the regenerated seeds; overwriting.")
        OUT_PATH.write_text(text, encoding="utf-8")
        print(f"wrote {len(registry)} records to {relative}")
        print(f"authoritative decisions: {len(registry.authoritative())} "
              "(expected 0)")
        return 0

    OUT_PATH.write_text(text, encoding="utf-8")
    print(f"wrote {len(registry)} records to {relative}")
    print(f"authoritative decisions: {len(registry.authoritative())} (expected 0)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
