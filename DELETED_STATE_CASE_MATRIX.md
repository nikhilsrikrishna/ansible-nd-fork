# Deleted State — Comprehensive Case Matrix

## Overview

The deleted state marks and/or removes policies on NDFC depending on `deploy`. It is **idempotent**: deleting an already-absent
policy is a no-op (`changed=false`). The module supports two deletion flows depending on
the `deploy` parameter:

| `deploy` | Flow | Steps | Effect |
|----------|------|-------|--------|
| `true` (default) | **4-step** | markDelete → pushConfig → remove → companion cleanup | Negation config pushed to switch, policy record deleted from NDFC, companion policies cleaned up |
| `false` | **1-step** | markDelete only | Policy record is flagged for deletion on NDFC; no pushConfig, no hard-delete |

> **Bulk execution**: All policy IDs to delete are collected first, then executed in bulk
> (not per-entry). With `deploy=true`, markDelete, pushConfig, and remove each happen once
> for all policies, followed by companion policy cleanup. With `deploy=false`, only markDelete
> runs once for all policies.

---

## Decision Factors

| # | Factor | Possible Values | Where Determined |
|---|--------|----------------|------------------|
| F1 | **`name`** (in config entry) | `None` / omitted, Policy ID (`POLICY-XXXX`), Template name (`switch_freeform`) | Playbook `config[].name` |
| F2 | **`use_desc_as_key`** | `true`, `false` (default) | Playbook top-level param |
| F3 | **`description`** (in config entry) | Empty / omitted (`""`), Non-empty string | Playbook `config[].description` |
| F4 | **Controller match count** | 0, 1, ≥2 | Result of `_build_have()` API query |
| F5 | **`deploy`** | `true` (default), `false` | Playbook top-level param |
| F6 | **`check_mode`** | `true`, `false` | Ansible `--check` flag |

### Factor Dependencies

```
name ──┬── None ──────────────── Case D (switch-only) → delete ALL policies on switch
       │
       ├── POLICY-XXXX ──────── Case A (direct ID lookup)
       │                          └── ignores use_desc_as_key, description
       │
       └── template_name ──┬── use_desc_as_key=false ── Case B (switchId + templateName)
                           │     └── description used as optional post-filter
                           │
                           └── use_desc_as_key=true ─── Case C (switchId + description)
                                 └── description REQUIRED (hard fail if empty)
                                 └── templateName NOT used as post-filter
                                       (diff logic handles template mismatch)
```

## Lookup Strategy Matrix (`_build_have`)

The lookup logic is **shared** with merged and query states. Only the diff and execution
phases differ.

| Case | name | use_desc_as_key | Lucene Filter | Post-Filters | Notes |
|------|------|-----------------|---------------|-------------|-------|
| **A** | `POLICY-XXXX` | _ignored_ | Direct `GET /policies/{id}` | `policyId in data` check | Single policy lookup by ID |
| **B** | template name | `false` | `switchId AND templateName` | Optional: exact `description` match | Returns all policies with that template on switch |
| **C** | template name | `true` | `switchId AND description` | Exact `description` match only | **No** templateName post-filter (unlike query state) |
| **D** | `None`/omitted | _ignored_ | `switchId` only | _none_ | Returns ALL policies on the switch |

> **Key difference from query state**: In Case C (deleted), `_build_have` does **not** post-filter
> by `templateName`. This is intentional — the user is saying "delete the policy with this
> description on this switch" regardless of which template it uses. Query state adds the
> template filter because it's a read-only narrowing operation.

---

## Validation Phase (Before Any API Calls)

### Upfront Validation (`_validate_config`)

These checks happen **atomically before** any API calls. If any check fails, the entire task
aborts with `fail_json` — no partial deletions occur.

| Check | Condition | Applies When | Failure Type | Error Message |
|-------|-----------|-------------|--------------|---------------|
| **V-1** | `config` is empty/missing | Always | Hard fail (`fail_json`) | `'config' element is mandatory for state 'deleted'` |
| **V-2** | Config entry has no `switch` after translation | Always | Hard fail (`fail_json`) | `config[N]: every policy entry must have a switch serial number after translation` |
| **V-3** | `use_desc_as_key=true` + empty description + name is template | `state in (merged, deleted)` | Hard fail (`fail_json`) | `config[N]: description cannot be empty when use_desc_as_key=true and name is a template name ('{name}')` |
| **V-4** | `use_desc_as_key=true` + duplicate `description+switch` pairs | Always | Hard fail (`fail_json`) | `Duplicate description+switch combinations found in the playbook config...` |

> **Atomicity guarantee**: V-3 and V-4 ensure the entire task fails before any API mutations.
> Without V-3, the module would make some deletions before hitting the missing-description
> error in `_build_have`. Without V-4, ambiguous descriptions could cause unexpected
> multi-policy deletions.

### Skipped Validations

| Condition | Why Skipped |
|-----------|-------------|
| `name` is a policy ID (`POLICY-XXXX`) | Direct ID lookup — description is irrelevant |
| `name` is `None`/omitted (switch-only) | No description needed — operating on all policies |
| `use_desc_as_key=false` | Description is optional, not a key |

---

## Complete Case Matrix

### Legend

- **changed**: `true` if policies were actually deleted, `false` if nothing to delete or check_mode
- **found**: Whether matching policies were located on the controller
- **action**: `delete` (single), `delete_all` (bulk), `skip` (absent), or `fail` (error)
- **Hard Fail**: `module.fail_json()` — aborts the **entire** task immediately, no results returned
- **Soft Fail**: `action=fail` with `success=false` — registers in results, task marked as failed but other entries still processed
- **Idempotent**: Re-running the same playbook produces `changed=false` (no-op)

---

### Group 1: Policy ID Given (`name = "POLICY-XXXX"`)

_Lookup: Case A — direct GET by policy ID. `use_desc_as_key` and `description` are ignored._

| Case | name | use_desc_as_key | description | Controller State | action | found | changed | Execution | Notes |
|------|------|-----------------|-------------|-----------------|--------|-------|---------|-----------|-------|
| **D-1** | `POLICY-1234` | `false` | _any_ | Policy exists | `delete` | ✅ | ✅ | 4-step or markDelete-only per `deploy` | Exact single policy deleted |
| **D-1a** | `POLICY-1234` | `true` | _any_ | Policy exists | `delete` | ✅ | ✅ | 4-step or markDelete-only per `deploy` | `use_desc_as_key` irrelevant for ID lookup |
| **D-2** | `POLICY-9999` | `false` | _any_ | Policy absent (404) | `skip` | ❌ | ❌ | No API calls | **Idempotent** — already absent, no error |
| **D-2a** | `POLICY-9999` | `true` | _any_ | Policy absent | `skip` | ❌ | ❌ | No API calls | Same — ID lookup ignores desc_as_key |
| **D-2b** | `POLICY-1234` | _any_ | _any_ | `markDeleted=true` | `skip` | ❌ | ❌ | No API calls | Treated as absent — pending deletion by another process |
| **D-2c** | `POLICY-1234` | _any_ | _any_ | Error obj (`code:404`) | `skip` | ❌ | ❌ | No API calls | Controller returns error body but HTTP 200 |

> **Idempotency**: D-2/D-2a/D-2b/D-2c are the idempotent cases — the policy doesn't exist
> (or is already being deleted), so the module reports success with `changed=false`.

---

### Group 2: Template Name, `use_desc_as_key=false`

_Lookup: Case B — Lucene filter by `switchId + templateName`. Description is an optional post-filter._

| Case | name | use_desc_as_key | description | Matches | action | found | changed | Execution | Notes |
|------|------|-----------------|-------------|---------|--------|-------|---------|-----------|-------|
| **D-3** | `switch_freeform` | `false` | _empty_ | 0 | `skip` | ❌ | ❌ | No API calls | **Idempotent** — no policies with that template |
| **D-4** | `switch_freeform` | `false` | _empty_ | 1 | `delete` | ✅ | ✅ | Deletes the single match | Single policy matched by template |
| **D-5** | `switch_freeform` | `false` | _empty_ | ≥2 | `delete_all` | ✅ | ✅ | Deletes ALL matches | **All** policies with that template on switch are deleted |
| **D-6** | `switch_freeform` | `false` | `"my-desc"` | ≥1 template match, 0 desc match | `skip` | ❌ | ❌ | No API calls | Description post-filter removed all matches |
| **D-7** | `switch_freeform` | `false` | `"my-desc"` | 1 template+desc match | `delete` | ✅ | ✅ | Deletes the match | Description narrows to exact policy |
| **D-8** | `switch_freeform` | `false` | `"my-desc"` | ≥2 template+desc match | `delete_all` | ✅ | ✅ | Deletes all matches | Rare: multiple policies with same template+desc |

> **Caution on D-5**: When `use_desc_as_key=false` and no description is given, **all** policies
> matching the template name on the switch are deleted. If there are 10 `switch_freeform`
> policies, all 10 are deleted. To delete a specific one, use its policy ID or provide a
> description filter.

---

### Group 3: Template Name, `use_desc_as_key=true`

_Lookup: Case C — Lucene filter by `switchId + description`, post-filtered by exact description match. `templateName` is NOT used as a post-filter (unlike query state)._

| Case | name | use_desc_as_key | description | Matches | action | found | changed | Failure Type | Notes |
|------|------|-----------------|-------------|---------|--------|-------|---------|-------------|-------|
| **D-9** | `switch_freeform` | `true` | _empty_ | _N/A_ | — | — | — | **Hard Fail** (V-3) | `_validate_config` catches this before any API calls |
| **D-10** | `switch_freeform` | `true` | `"my-desc"` | 0 | `skip` | ❌ | ❌ | — | **Idempotent** — no policy with that desc on switch |
| **D-11** | `switch_freeform` | `true` | `"my-desc"` | 1 exact match | `delete` | ✅ | ✅ | — | Ideal case — desc uniquely identifies the policy |
| **D-12** | `switch_freeform` | `true` | `"my-desc"` | ≥2 exact matches | — | — | — | **Hard Fail** (`fail_json`) | Ambiguous — cannot determine which to delete |

> **D-9 vs D-12 failure points**:
> - D-9 (empty description) is caught by `_validate_config()` — **before** any API calls.
> - D-12 (multiple matches) is caught by `_get_diff_deleted_single()` — **after** the API
>   query but **before** any mutations. Both are hard fails that abort the entire task.
>
> **Why D-12 is a hard fail**: When `use_desc_as_key=true`, descriptions should be unique
> per switch. Multiple matches mean the NDFC state is inconsistent (duplicates created outside
> of this module). Silently deleting all matches would be dangerous. The user must resolve
> the ambiguity by either:
> 1. Using a policy ID (`POLICY-XXXX`) to target a specific policy
> 2. Removing the duplicates from NDFC manually
> 3. Using `use_desc_as_key=false` with `name` omitted to delete all

---

### Group 4: Switch-Only (`name` omitted / `None`)

_Lookup: Case D — Lucene filter by `switchId` only. Returns everything on the switch. `use_desc_as_key` and `description` are ignored._

| Case | name | use_desc_as_key | description | Policies on switch | action | found | changed | Execution | Notes |
|------|------|-----------------|-------------|-------------------|--------|-------|---------|-----------|-------|
| **D-13** | _omitted_ | `false` | _any_ | ≥1 | `delete_all` | ✅ | ✅ | Deletes ALL policies on switch | **Nuclear option** — wipes everything |
| **D-13a** | _omitted_ | `true` | _any_ | ≥1 | `delete_all` | ✅ | ✅ | Deletes ALL policies on switch | `use_desc_as_key` irrelevant for switch-only |
| **D-14** | _omitted_ | _any_ | _any_ | 0 | `skip` | ❌ | ❌ | No API calls | **Idempotent** — switch already clean |

> **Caution on D-13**: This deletes **all** policies on the switch — not just policies managed
> by this module. System policies, policies created by other modules, manually created
> policies — everything. Use with extreme care.

---

## Execution Phase Detail

### Check Mode (`--check`)

When Ansible check mode is active, **no API calls are made**. The module reports what
**would** happen:

| Scenario | Result |
|----------|--------|
| Policies found to delete | `changed=true`, `message="OK (check_mode)"`, diff shows `policy_ids` |
| No policies to delete (skip) | `changed=false`, `message="Policy not found — already absent"` |
| Validation failure (V-3, D-9, D-12) | Still hard fails — validation runs even in check mode |

### Normal Execution (deploy=true)

```
Phase A: Compute diffs (per config entry)
│  ├── For each config entry:
│  │   ├── _build_want(entry, state="deleted")
│  │   ├── _build_have(want) → have_list
│  │   └── _get_diff_deleted_single(want, have_list) → action + policy_ids
│  │
│  ├── action=fail   → register error result (soft fail)
│  ├── action=skip   → register "already absent" result
│  └── action=delete/delete_all → collect policy_ids into bulk list
│
Phase B: Bulk execution (all collected policy IDs at once)
│  ├── Deduplicate policy IDs (same policy could match multiple entries)
│  │
│  ├── Step 1: POST /policyActions/markDelete
│  │   └── Flags policies for deletion on controller
│  │   └── Result registered: action="mark_delete"
│  │
│  ├── Step 2: POST /policyActions/pushConfig
│  │   └── Pushes negation config to switches (removes running config)
│  │   └── Result registered: action="deploy"
│  │
│  ├── Step 3: POST /policyActions/remove
│  │   └── Hard-deletes policy records from NDFC database
│  │   └── Result registered: action="remove"
│  │
│  └── Step 4: Companion policy cleanup
│      └── Queries each affected switch for policies whose `source` matches a removed parent ID
│      └── Deletes each companion via DELETE /policies/{policyId}
│      └── Result registered: action="policy_shadow_cleanup"
│      └── Only applies to PYTHON content-type templates (e.g., switch_freeform)
```

### Normal Execution (deploy=false)

```
Phase A: Same as above
│
Phase B: Bulk execution (simplified)
│  └── Step 1: POST /policyActions/markDelete
│      └── Flags policy records for deletion on controller
│      └── No pushConfig, no remove; switch running config is NOT affected
```

> **When to use `deploy=false`**: If you only want to clean up stale policy records from
> NDFC without affecting the switches and without hard-deleting immediately (e.g., staged
> cleanup workflows, deferred removal).

---

## Deduplication

When multiple config entries resolve to the same policy ID, the module deduplicates before
making API calls:

```yaml
config:
  - name: switch_freeform          # matches POLICY-100, POLICY-200
  - name: POLICY-100               # explicit ID — same as above
  - switch:
      - serial_number: FDO29080NBU
```

The module collects `[POLICY-100, POLICY-200, POLICY-100]` and deduplicates to
`[POLICY-100, POLICY-200]`. Only one markDelete/pushConfig/remove call is made for each
unique policy ID.

---

## Full Decision Flowchart

```
START: state=deleted, config entries received
│
├─ V-1: config missing? ────────────────────────── HARD FAIL (module-level)
├─ V-2: no switch after translation? ──────────── HARD FAIL (module-level)
├─ V-3: use_desc_as_key + empty desc + template?── HARD FAIL (module-level, atomic)
├─ V-4: use_desc_as_key + dup desc+switch? ─────── HARD FAIL (module-level, atomic)
│
│  FOR EACH config entry:
│  │
│  │  _build_want(config_entry, state="deleted")
│  │  ├── name is POLICY-XXXX → want = {policyId, switchId}
│  │  ├── name is template    → want = {templateName, switchId, [description]}
│  │  └── name is None        → want = {switchId}
│  │
│  │  _build_have(want)
│  │  ├── policyId in want? ─── Case A ─── GET /policies/{id}
│  │  │   ├── found + not markDeleted  → have = [{policy}]
│  │  │   └── not found / markDeleted  → have = []
│  │  │
│  │  ├── templateName NOT in want? ─── Case D ─── Lucene: switchId
│  │  │   └── returns ALL policies on switch (filtered: no markDeleted, no source!="")
│  │  │
│  │  ├── use_desc_as_key=false? ─── Case B ─── Lucene: switchId + templateName
│  │  │   ├── description provided? → post-filter by exact description
│  │  │   └── returns matching policies
│  │  │
│  │  └── use_desc_as_key=true? ─── Case C ─── Lucene: switchId + description
│  │      ├── description empty? → error (but caught by V-3 already)
│  │      └── post-filter: exact description match (NO templateName filter)
│  │
│  │  _get_diff_deleted_single(want, have_list)
│  │  ├── policyId in want?
│  │  │   ├── match ≥ 1 → D-1:  action=delete, policy_ids=[{id}]
│  │  │   └── match = 0 → D-2:  action=skip
│  │  │
│  │  ├── templateName NOT in want? (switch-only)
│  │  │   ├── match ≥ 1 → D-13: action=delete_all, policy_ids=[all on switch]
│  │  │   └── match = 0 → D-14: action=skip
│  │  │
│  │  ├── use_desc_as_key=false?
│  │  │   ├── match = 0  → D-3: action=skip
│  │  │   ├── match = 1  → D-4: action=delete
│  │  │   └── match ≥ 2  → D-5: action=delete_all
│  │  │
│  │  └── use_desc_as_key=true?
│  │      ├── desc empty? → D-9:  HARD FAIL (caught by V-3 — should not reach here)
│  │      ├── match = 0   → D-10: action=skip
│  │      ├── match = 1   → D-11: action=delete
│  │      └── match ≥ 2   → D-12: HARD FAIL (fail_json — ambiguous)
│  │
│  │  Collect results:
│  │  ├── action=fail      → register(success=false), continue to next entry
│  │  ├── action=skip      → register(success=true, found=false, changed=false)
│  │  └── action=delete/delete_all → register intent, add policy_ids to bulk list
│  │
│  END FOR
│
│  BULK EXECUTION (if not check_mode AND policy_ids collected):
│  ├── Deduplicate policy IDs
│  ├── deploy=true?
│  │   ├── Step 1: markDelete(policy_ids)     ← flag for deletion
│  │   ├── Step 2: pushConfig(policy_ids)     ← remove config from switches
│  │   ├── Step 3: remove(policy_ids)         ← hard-delete from NDFC
│  │   └── Step 4: companion cleanup          ← delete companion policies for PYTHON templates
│  └── deploy=false?
│      └── Step 1: markDelete(policy_ids)     ← flag for deletion only
│
END: module.exit_json(changed=..., results=...)
```

---

## Summary Table: All Deleted Cases

| Case | Lookup | name | use_desc_as_key | description | Controller State | action | found | changed | success | Failure | Idempotent? |
|------|--------|------|-----------------|-------------|-----------------|--------|-------|---------|---------|---------|-------------|
| **D-1** | A | `POLICY-1234` | _any_ | _any_ | Policy exists | `delete` | ✅ | ✅ | ✅ | — | 2nd run → D-2 (skip) |
| **D-2** | A | `POLICY-9999` | _any_ | _any_ | Policy absent | `skip` | ❌ | ❌ | ✅ | — | ✅ Already idempotent |
| **D-2b** | A | `POLICY-1234` | _any_ | _any_ | markDeleted=true | `skip` | ❌ | ❌ | ✅ | — | ✅ Pending deletion |
| **D-2c** | A | `POLICY-1234` | _any_ | _any_ | Error obj (code:404) | `skip` | ❌ | ❌ | ✅ | — | ✅ |
| **D-3** | B | template | `false` | _empty_ | 0 matches | `skip` | ❌ | ❌ | ✅ | — | ✅ Already idempotent |
| **D-4** | B | template | `false` | _empty_ | 1 match | `delete` | ✅ | ✅ | ✅ | — | 2nd run → D-3 (skip) |
| **D-5** | B | template | `false` | _empty_ | ≥2 matches | `delete_all` | ✅ | ✅ | ✅ | — | 2nd run → D-3 (skip) |
| **D-6** | B | template | `false` | `"desc"` | template matches, desc doesn't | `skip` | ❌ | ❌ | ✅ | — | ✅ |
| **D-7** | B | template | `false` | `"desc"` | 1 template+desc match | `delete` | ✅ | ✅ | ✅ | — | 2nd run → D-6 (skip) |
| **D-8** | B | template | `false` | `"desc"` | ≥2 template+desc match | `delete_all` | ✅ | ✅ | ✅ | — | 2nd run → D-6 (skip) |
| **D-9** | — | template | `true` | _empty_ | _N/A_ | — | — | — | ❌ | **Hard Fail** (V-3) | N/A |
| **D-10** | C | template | `true` | `"desc"` | 0 matches | `skip` | ❌ | ❌ | ✅ | — | ✅ Already idempotent |
| **D-11** | C | template | `true` | `"desc"` | 1 exact match | `delete` | ✅ | ✅ | ✅ | — | 2nd run → D-10 (skip) |
| **D-12** | C | template | `true` | `"desc"` | ≥2 exact matches | — | — | — | ❌ | **Hard Fail** | N/A (user must fix) |
| **D-13** | D | _omitted_ | _any_ | _any_ | ≥1 on switch | `delete_all` | ✅ | ✅ | ✅ | — | 2nd run → D-14 (skip) |
| **D-14** | D | _omitted_ | _any_ | _any_ | 0 on switch | `skip` | ❌ | ❌ | ✅ | — | ✅ Already idempotent |
| | | | | | | | | | | | |
| **V-1** | — | — | — | — | — | — | — | — | ❌ | **Hard Fail** | config missing |
| **V-2** | — | — | — | — | — | — | — | — | ❌ | **Hard Fail** | no switch |
| **V-3** | — | template | `true` | _empty_ | — | — | — | — | ❌ | **Hard Fail** | empty desc |
| **V-4** | — | _any_ | `true` | dup desc+sw | — | — | — | — | ❌ | **Hard Fail** | dup desc |

---

## Idempotency Analysis

Every case is idempotent — running the same playbook twice produces `changed=false` on the
second run:

| First Run | Second Run | Why Idempotent |
|-----------|------------|----------------|
| D-1 (delete by ID) | D-2 (skip — absent) | Policy no longer exists |
| D-4 (delete 1 by template) | D-3 (skip — 0 matches) | No policies with that template remain |
| D-5 (delete_all by template) | D-3 (skip — 0 matches) | All policies with that template gone |
| D-7 (delete by template+desc) | D-6 (skip — desc doesn't match) | Policy no longer exists |
| D-11 (delete by desc key) | D-10 (skip — 0 desc matches) | Policy no longer exists |
| D-13 (delete_all on switch) | D-14 (skip — 0 on switch) | Switch has no policies |

---

## Consistency & Safety Guarantees

### 1. Atomic Validation (No Partial Deletions from Config Errors)

```
_validate_config() runs BEFORE any _build_have() or API calls.
If ANY config entry has:
  - empty description when use_desc_as_key=true (V-3)
  - duplicate description+switch pair (V-4)
→ The ENTIRE task fails. Zero policies are deleted.
```

### 2. Hard Fail on Ambiguity (D-12)

When `use_desc_as_key=true` and multiple policies share the same description on a switch,
the module **hard fails** (`fail_json`) rather than guessing which to delete. This prevents
accidental data loss.

```
D-12: 2 policies with description "enable-lacp" on FDO29080NBU
→ FAIL: "Multiple policies (2) found with description 'enable-lacp'
   on switch FDO29080NBU. Descriptions must be unique per switch when
   use_desc_as_key=true."
```

### 3. markDeleted Filter (No Double-Deletion)

Policies already flagged with `markDeleted=true` are **excluded** from `_build_have` results.
This prevents the module from trying to re-delete a policy that's already being removed
by another process or a previous run.

### 4. Source Filter (No Shadow Policy Deletion)

Policies with `source != ""` are excluded from `_build_have` results during diff calculation.
This prevents the module from treating NDFC-managed companion policies as user-managed entries.

For PYTHON content-type templates (e.g., `switch_freeform`), NDFC automatically creates
a companion `switch_freeform_config` policy with:
- `source` = parent `switch_freeform` policy ID
- `templateName` = `switch_freeform_config`
- `templateContentType` = `TEMPLATE_CLI`
- Negative `priority` (e.g., `-10940` when parent is `POLICY-10940`)

These companions are:
- **Excluded** from `_build_have` results (source filter) — they are never treated as
  user-managed policies for diff/idempotency checks
- **Cleaned up automatically** in Step 4 of the delete flow (`deploy=true`) — after the
  parent is removed, the module queries affected switches for orphaned companions whose
  `source` matches a removed parent ID and deletes them via `DELETE /policies/{policyId}`
- **Not cleaned up** when `deploy=false` — only markDelete is performed, companions remain

Other template content types (`TEMPLATE_CLI`, `TEXT`) do not create companion policies.

### 5. Deduplication (No Redundant API Calls)

If multiple config entries resolve to the same policy ID, the ID appears only once in the
bulk API calls. This prevents 207 Multi-Status errors from trying to delete the same
policy twice.

---

## Playbook Examples

### D-1: Delete by Policy ID
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    state: deleted
    config:
      - name: POLICY-10940
      - switch:
          - serial_number: FDO29080NBU
# → changed=true, deletes POLICY-10940
# Re-run → changed=false (D-2: skip, already absent)
```

### D-4/D-5: Delete by Template Name
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    state: deleted
    config:
      - name: switch_freeform
      - switch:
          - serial_number: FDO29080NBU
# → changed=true, deletes ALL switch_freeform policies on FDO29080NBU
# Re-run → changed=false (D-3: skip, 0 matches)
```

### D-7: Delete by Template Name + Description Filter
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    state: deleted
    config:
      - name: switch_freeform
        description: "enable-lacp"
      - switch:
          - serial_number: FDO29080NBU
# → Deletes only the switch_freeform policy with description "enable-lacp"
# Other switch_freeform policies on the switch are untouched
```

### D-11: Delete by Description Key
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    use_desc_as_key: true
    state: deleted
    config:
      - name: switch_freeform
        description: "enable-lacp"
      - switch:
          - serial_number: FDO29080NBU
# → Deletes the policy with description "enable-lacp" (regardless of template)
# Re-run → changed=false (D-10: skip, 0 matches)
```

### D-13: Delete ALL Policies on Switch (Nuclear Option)
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    state: deleted
    config:
      - switch:
          - serial_number: FDO29080NBU
# → changed=true, deletes EVERY policy on FDO29080NBU
# ⚠ CAUTION: This includes system policies, policies from other modules, etc.
# Re-run → changed=false (D-14: skip, 0 on switch)
```

### D-9: Hard Fail — Empty Description with desc_as_key
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    use_desc_as_key: true
    state: deleted
    config:
      - name: switch_freeform
        # description intentionally omitted
      - switch:
          - serial_number: FDO29080NBU
# → HARD FAIL: "config[0]: description cannot be empty when use_desc_as_key=true"
# Zero policies deleted — atomic failure before any API calls
```

### deploy=false: Mark Policies for Deletion Only
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    state: deleted
    deploy: false
    config:
      - name: switch_freeform
      - switch:
          - serial_number: FDO29080NBU
    # → Policies are markDeleted on NDFC; no pushConfig/remove API call
    # → Switch running config is NOT changed
```

### Check Mode: Preview Deletions
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    state: deleted
    config:
      - name: switch_freeform
      - switch:
          - serial_number: FDO29080NBU
  check_mode: true
# → changed=true (would delete), but no actual API calls made
# diff shows which policy_ids would be deleted
```

---

## Key Behavioral Notes

1. **Deleted state is inherently idempotent**: Deleting an absent policy is a successful no-op.
   Every delete case has a corresponding skip case for the second run.

2. **`use_desc_as_key` only matters when `name` is a template name**: If `name` is a policy
   ID (Case A) or omitted (Case D), the flag is completely ignored.

3. **Case C: No templateName post-filter (unlike query)**: When `use_desc_as_key=true`,
   deleted state uses description alone to find the policy. This is intentional — the user
   says "delete the policy with this description" regardless of template. If the template
   changed (e.g., via `delete_and_create` in merged state), the description still identifies it.

4. **Two hard fail points**:
   - `_validate_config()` (V-3, V-4) — before any API calls, atomic
   - `_get_diff_deleted_single()` (D-12) — after query, before mutations

5. **Bulk execution**: Individual config entries are processed for diff calculation, but the
  actual API calls happen once in bulk for all collected policy IDs. For `deploy=true`,
  markDelete + pushConfig + remove run once each, followed by companion policy cleanup;
  for `deploy=false`, only markDelete runs.

6. **deploy=true vs deploy=false**:
   - `deploy=true`: Config is removed from switches first (markDelete + pushConfig), then
     records are deleted from NDFC (remove), and finally companion policies for PYTHON
     content-type templates are cleaned up. This is the safe default.
   - `deploy=false`: Policies are only marked for deletion on NDFC (markDelete).
     No pushConfig, no hard-delete, and no companion cleanup are performed in this run.

7. **Multi-switch expansion**: If the switch list has multiple switches, `_translate_config`
   expands each policy entry into one entry per switch. Each expanded entry goes through
   the full delete pipeline independently, but all resulting policy IDs are collected into
   a single bulk API call.
