# RC-E: bootstrap-v0 + ADR-012 Evidence

## bootstrap-v0

### File path
`policies/bootstrap-v0.json`

### Version/name
- `policy_name`: `bootstrap-v0`
- `version`: `0`
- `schema_version`: `1`
- `status`: `PROPOSED`

### Relevant schema/keys
```json
{
  "policy_name": "bootstrap-v0",
  "version": "0",
  "schema_version": "1",
  "created_by": "P2.0 entry sequence per v4.1 AM-13.2",
  "created_at": "2026-09-05",
  "status": "PROPOSED",
  "supersedes": null,
  "superseded_by": "Scope v0 (P3, v4 §14.3)",
  "scope": {
    "description": "...",
    "applies_to": [...],
    "exclusions": [...]
  },
  "rules": [...],
  "default_decision": "deny",
  "invariants_enforced": [...],
  "retirement": {...},
  "references": {...}
}
```

### Default-deny behavior
- `default_decision`: `deny`
- Every rule has explicit `decision: "allow"` AND non-empty `constraints`
- No rule is unrestricted allow
- Fail-closed by default

### Confirmation: NOT allow-all
- All 5 rules have `constraints` blocks (non-empty)
- `default_decision` is `deny`
- `exclusions` list explicitly bars production capabilities, real subprocess, Decepticon
- `retirement.not_extended_past_P2: true`

### Intended P2 role
Per v4.1 AM-13.2: "define and commit a minimal named, versioned policy artifact
(`bootstrap-v0`) that the P2 Broker-mediated mock path and the P2.4 safe
capability authorize against."

- `applies_to`:
  - `P2.3 Broker-mediated mock path (v4 §13.3)`
  - `P2.4 Safe proving capability (v4 §13.3)`

### Explicit P3 supersession
- `superseded_by`: `Scope v0 (P3, v4 §14.3)`
- `retirement.retired_at`: `P3 (when Scope v0 lands per v4 §14.3)`
- `retirement.retired_by`: `Scope v0`
- `retirement.not_extended_past_P2`: `true`
- `retirement.rationale`: `Per v4.1 AM-13.2: bootstrap-v0 is not extended or reused past P2; it is retired when Scope v0 lands.`

### Rules (5 total, all with constraints)

| Rule ID | Action class | Decision | Constraints |
|---|---|---|---|
| BOOT-001 | mock_capability | allow | read_only, no_network, no_subprocess, deterministic_output |
| BOOT-002 | safe_proving_capability | allow | read_only_fixture_inspection, no_external_network, receipt_generation_required |
| BOOT-003 | stage_observation | allow | no_execution |
| BOOT-004 | worldmodel_read | allow | read_only |
| BOOT-005 | receipt_emission | allow | receipt_required, decision_id_required |

### Invariants enforced
INV-1, INV-2, INV-3, INV-5, INV-6, INV-7

### Commit
- Commit: `42f0d13fc3e8dc133ed609902fc9e84bc8af8d29` (P2.0 step 5)
- File SHA256: (compute at end of evidence)

## ADR-012

### File path
`docs/adr/ADR-012-seam-semantics-ratification.md`

### Complete text
See `docs/adr/ADR-012-seam-semantics-ratification.md` (178 lines, 4832 bytes).
The ADR is also copied to `evidence/g1_corrections/ADR-012-seam-semantics-ratification.md`
for the G1 corrections evidence package.

### Statement: seam-semantics substitution was formally ratified
ADR-012 Status: **Accepted (per v4.1 AM-4)**

ADR-012 explicitly states: "v4.1 AM-4: 'This is judged the single highest-priority
amendment in the set.'... This ADR ratifies v4.1 AM-4 as the canonical seam
contract."

The ADR codifies all 5 sub-decisions of v4.1 AM-4:
1. Positive interface (single typed proxy `SeamRoute(legacy_site_id) -> PolicyDecision`)
2. Weld semantics (3-part: fixed ON, legacy branch deleted, named policy artifact)
3. G3 exit condition (no partial welding)
4. Rollback discipline (rework Broker-mediated path, never re-open legacy branch)
5. Deletion (atomic, at last welded site)

### No silent architecture amendment
ADR-012 is an EXPLICIT ratification of v4.1 AM-4. It does not amend the
v4 architecture; it ratifies the v4.1 amendment layer. The v4.1 document
itself states: "this document is purely an amendment layer — v4 plus
AM-1 through AM-14 is the canonical roadmap going forward (v4.1), not
a replacement document."

ADR-012 references the v4.1 AM-4 text and provides a local copy for the
RAPHAEL repository. The ADR is a documentation artifact, not a code change.

## RC-E: NO P3 POLICY WORK PERFORMED

This is evidence work only. The bootstrap-v0 policy artifact is a P2
deliverable (v4.1 AM-13.2) that will be RETIRED at P3 when Scope v0
lands. The ADR-012 codifies the weld discipline but no welding occurred.

No P3 policy work was performed.
