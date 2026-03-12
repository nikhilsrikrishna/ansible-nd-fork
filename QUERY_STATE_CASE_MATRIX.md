# Query State — Comprehensive Case Matrix

## Decision Factors

The query state outcome is determined by the combination of these input factors:

| # | Factor | Possible Values | Where Determined |
|---|--------|----------------|------------------|
| F1 | **`name`** (in config entry) | `None` / omitted, Policy ID (`POLICY-XXXX`), Template name (`switch_freeform`) | Playbook `config[].name` |
| F2 | **`use_desc_as_key`** | `true`, `false` (default) | Playbook top-level param |
| F3 | **`description`** (in config entry) | Empty / omitted (`""`), Non-empty string | Playbook `config[].description` |
| F4 | **Controller match count** | 0, 1, ≥2 | Result of `_build_have()` API query |

### Factor Dependencies

```
name ──┬── None ──────────────── Case D (switch-only)
       │
       ├── POLICY-XXXX ──────── Case A (direct ID lookup)
       │                          └── ignores use_desc_as_key, description
       │
       └── template_name ──┬── use_desc_as_key=false ── Case B (switchId + templateName)
                           │     └── description used as optional post-filter
                           │
                           └── use_desc_as_key=true ─── Case C (switchId + description)
                                 └── description required
                                 └── templateName used as additional post-filter
```

## Lookup Strategy Matrix (`_build_have`)

| Case | name | use_desc_as_key | Lucene Filter | Post-Filters | Notes |
|------|------|-----------------|---------------|-------------|-------|
| **A** | `POLICY-XXXX` | _ignored_ | Direct `GET /policies/{id}` | `policyId in data` check | Single policy lookup by ID |
| **B** | template name | `false` | `switchId AND templateName` | Optional: exact `description` match | Returns all policies with that template on switch |
| **C** | template name | `true` | `switchId AND description` | Exact `description` match, then `templateName` match | Narrows by desc first, then template |
| **D** | `None`/omitted | _ignored_ | `switchId` only | _none_ | Returns ALL policies on the switch |

## Complete Case Matrix

### Legend

- **changed**: Always `false` for query state (read-only)
- **found**: Whether matching policies were located
- **action**: `found`, `not_found`, or `fail`
- **DATA**: What goes into `response[].DATA`
- **⚠**: Warning attached to result

---

### Group 1: Policy ID Given (`name = "POLICY-XXXX"`)

_Lookup: Case A — direct GET by policy ID. `use_desc_as_key` and `description` are ignored._

| Case | name | use_desc_as_key | description | Controller has policy? | action | found | DATA | Notes |
|------|------|-----------------|-------------|----------------------|--------|-------|------|-------|
| **Q-1** | `POLICY-1234` | `false` | _any_ | Yes (valid policy dict with `policyId` key) | `found` | `true` | `[{policy}]` | Direct ID hit |
| **Q-1a** | `POLICY-1234` | `true` | _any_ | Yes | `found` | `true` | `[{policy}]` | `use_desc_as_key` irrelevant for ID lookup |
| **Q-2** | `POLICY-9999` | `false` | _any_ | No (404 or `policyId` missing from response) | `not_found` | `false` | `{}` | Policy doesn't exist |
| **Q-2a** | `POLICY-9999` | `true` | _any_ | No | `not_found` | `false` | `{}` | Same — ID lookup ignores desc_as_key |
| **Q-2b** | `POLICY-1234` | _any_ | _any_ | Deleted (`markDeleted=true`) | `not_found` | `false` | `{}` | `_query_policy_by_id` returns `None` for markDeleted |
| **Q-2c** | `POLICY-1234` | _any_ | _any_ | Controller returns `{code: 404, message: "..."}` (HTTP 200) | `not_found` | `false` | `{}` | Bug 7 fix: `policyId not in data` → treated as not found |

---

### Group 2: Switch-Only (`name` omitted / `None`)

_Lookup: Case D — Lucene filter by `switchId` only. Returns everything on the switch. `use_desc_as_key` and `description` are ignored._

| Case | name | use_desc_as_key | description | Policies on switch | action | found | DATA | Notes |
|------|------|-----------------|-------------|-------------------|--------|-------|------|-------|
| **Q-3** | _omitted_ | `false` | _any_ | ≥1 | `found` | `true` | `[{p1}, {p2}, ...]` | All policies on switch returned |
| **Q-3a** | _omitted_ | `true` | _any_ | ≥1 | `found` | `true` | `[{p1}, {p2}, ...]` | Same — switch-only ignores desc_as_key |
| **Q-4** | _omitted_ | _any_ | _any_ | 0 | `not_found` | `false` | `{}` | Switch has no policies |

> **Note:** Switch-only queries return **all** policy types (including system policies like `switch_migration_state`). The user cannot filter by template in this mode.

---

### Group 3: Template Name, `use_desc_as_key=false`

_Lookup: Case B — Lucene filter by `switchId + templateName`. Description is an optional post-filter._

| Case | name | use_desc_as_key | description | Matches on controller | action | found | DATA | Notes |
|------|------|-----------------|-------------|----------------------|--------|-------|------|-------|
| **Q-5** | `switch_freeform` | `false` | _empty_ | 0 | `not_found` | `false` | `{}` | No policies with that template on switch |
| **Q-6** | `switch_freeform` | `false` | _empty_ | 1 | `found` | `true` | `[{policy}]` | Single match |
| **Q-7** | `switch_freeform` | `false` | _empty_ | ≥2 | `found` | `true` | `[{p1}, {p2}, ...]` | Multiple policies with same template — all returned |
| **Q-8** | `switch_freeform` | `false` | `"my-desc"` | ≥1 matching template, 0 matching desc | `not_found` | `false` | `{}` | Description post-filter removes all matches |
| **Q-9** | `switch_freeform` | `false` | `"my-desc"` | ≥1 matching template, 1 matching desc | `found` | `true` | `[{policy}]` | Description narrows to exact match |
| **Q-10** | `switch_freeform` | `false` | `"my-desc"` | ≥1 matching template, ≥2 matching desc | `found` | `true` | `[{p1}, {p2}]` | Multiple policies with same template+desc (rare but valid) |

> **Note:** When `use_desc_as_key=false` and description is provided, description acts as an **optional refinement filter** on the template-based results. No validation error is raised for empty/missing descriptions.

---

### Group 4: Template Name, `use_desc_as_key=true`

_Lookup: Case C — Lucene filter by `switchId + description`, then post-filtered by exact description match, then by `templateName` match (query state only)._

| Case | name | use_desc_as_key | description | Matches on controller | action | found | DATA | Warning | Notes |
|------|------|-----------------|-------------|----------------------|--------|-------|------|---------|-------|
| **Q-11** | `switch_freeform` | `true` | _empty_ | _N/A_ | `fail` | `false` | `{}` | — | `_get_diff_query_single` returns fail: "description is required when use_desc_as_key=true" |
| **Q-12** | `switch_freeform` | `true` | `"my-desc"` | 0 (no policy with that desc+template on switch) | `not_found` | `false` | `{}` | — | Lucene found nothing, or post-filters removed all |
| **Q-12a** | `switch_freeform` | `true` | `"my-desc"` | desc matches but template doesn't (e.g., policy is `feature_enable`) | `not_found` | `false` | `{}` | — | templateName post-filter (query-only) removes the match |
| **Q-13** | `switch_freeform` | `true` | `"my-desc"` | 1 exact match (desc + template) | `found` | `true` | `[{policy}]` | — | Ideal case — unique desc identifies exactly one policy |
| **Q-14** | `switch_freeform` | `true` | `"my-desc"` | ≥2 exact matches (same desc + same template) | `found` | `true` | `[{p1}, {p2}]` | ⚠ "Multiple policies (N) found with description..." | Returns all matches but warns about non-unique descriptions |

> **Note on Q-11:** The empty-description check happens in `_get_diff_query_single` (not `_validate_config`), because `_validate_config` only enforces description requirements for `merged`/`deleted` states. For query state, the check is soft — it returns `action=fail` in the result but doesn't `fail_json` the entire task. However, looking at `_execute_query`, action `fail` registers with `success=False`, causing the module to fail.
>
> **Wait — let me verify that.** Actually, `_validate_config` checks `self.state in ("merged", "deleted")` for empty description, so query state with empty desc passes `_validate_config`. But then `_build_have` Case C returns error `"description is required when use_desc_as_key=true..."`, and `_handle_query_state` wraps it as `action=fail`. Then `_execute_query` registers it with `success=False`, and `_register_result` with `success=False` causes the module to set `failed=True`.

---

### Group 5: Upstream Validation Failures (before `_build_have`)

These failures happen during argument validation or `_translate_config`, before the query logic even runs:

| Case | Condition | Failure Point | Error Message |
|------|-----------|---------------|---------------|
| **V-1** | `config` is empty/missing | `main()` | `'config' element is mandatory for state 'query'` |
| **V-2** | Config entry has no `switch` after translation | `main()` | `config[N]: every policy entry must have a switch serial number after translation` |
| **V-3** | `use_desc_as_key=true` + duplicate `description+switch` pairs in config | `_validate_config()` | `Duplicate description+switch combinations found...` |

> **Note:** `_validate_config` does NOT require description for query state even when `use_desc_as_key=true` — that check is `merged`/`deleted` only.

---

## Full Decision Flowchart

```
START: state=query, config entry received
│
├─ V-1: config missing? ──────────────────────── FAIL (module-level)
├─ V-2: no switch after translation? ─────────── FAIL (module-level)
├─ V-3: use_desc_as_key + dup desc+switch? ───── FAIL (module-level)
│
│  _build_want(config_entry, state="query")
│  ├── name is POLICY-XXXX → want = {policyId, switchId}
│  ├── name is template    → want = {templateName, switchId, [description]}
│  └── name is None        → want = {switchId}
│
│  _build_have(want)
│  ├── policyId in want? ─── Case A ─── GET /policies/{id}
│  │   ├── valid policy dict with policyId key → have = [{policy}]
│  │   ├── markDeleted=true                    → have = []
│  │   ├── error response (code:404, no policyId) → have = []
│  │   └── HTTP 404                            → have = []
│  │
│  ├── templateName NOT in want? ─── Case D ─── Lucene: switchId
│  │   └── returns all policies on switch
│  │
│  ├── use_desc_as_key=false? ─── Case B ─── Lucene: switchId + templateName
│  │   ├── description provided? → post-filter by exact description
│  │   └── returns matching policies
│  │
│  └── use_desc_as_key=true? ─── Case C ─── Lucene: switchId + description
│      ├── description empty? → error: "description is required..."
│      ├── post-filter: exact description match
│      └── post-filter: templateName match (query state only)
│
│  _get_diff_query_single(want, have_list)
│  ├── policyId in want?
│  │   ├── match ≥ 1 → Q-1: found
│  │   └── match = 0 → Q-2: not_found
│  │
│  ├── templateName NOT in want? (switch-only)
│  │   ├── match ≥ 1 → Q-3: found
│  │   └── match = 0 → Q-4: not_found
│  │
│  ├── use_desc_as_key=false?
│  │   ├── match > 0 → Q-5/6/7: found
│  │   └── match = 0 → Q-8: not_found
│  │
│  └── use_desc_as_key=true?
│      ├── description empty? → Q-11: fail
│      ├── match = 0  → Q-12: not_found
│      ├── match = 1  → Q-13: found
│      └── match ≥ 2  → Q-14: found + warning ⚠
│
│  _execute_query(diff_results)
│  ├── action=fail      → register(success=false, found=false) → module FAILS
│  ├── action=not_found → register(success=true,  found=false, DATA={})
│  └── action=found     → register(success=true,  found=true,  DATA=[policies])
│
END: module.exit_json(changed=false, ...)
```

---

## Summary Table: All 14 Query Cases + 3 Validation Cases

| Case | Lookup | name | use_desc_as_key | description | Controller State | action | found | changed | success | DATA | ⚠ |
|------|--------|------|-----------------|-------------|-----------------|--------|-------|---------|---------|------|---|
| **Q-1** | A | `POLICY-1234` | _any_ | _any_ | Policy exists | `found` | ✅ | ❌ | ✅ | `[{policy}]` | |
| **Q-2** | A | `POLICY-9999` | _any_ | _any_ | Policy absent | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-2b** | A | `POLICY-1234` | _any_ | _any_ | markDeleted=true | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-2c** | A | `POLICY-1234` | _any_ | _any_ | Error obj (code:404) | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-3** | D | _omitted_ | _any_ | _any_ | ≥1 policies on switch | `found` | ✅ | ❌ | ✅ | `[{p1},...]` | |
| **Q-4** | D | _omitted_ | _any_ | _any_ | 0 policies on switch | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-5** | B | template | `false` | _empty_ | 0 matches | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-6** | B | template | `false` | _empty_ | 1 match | `found` | ✅ | ❌ | ✅ | `[{policy}]` | |
| **Q-7** | B | template | `false` | _empty_ | ≥2 matches | `found` | ✅ | ❌ | ✅ | `[{p1},{p2}]` | |
| **Q-8** | B | template | `false` | `"desc"` | matches template, 0 match desc | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-9** | B | template | `false` | `"desc"` | 1 match template+desc | `found` | ✅ | ❌ | ✅ | `[{policy}]` | |
| **Q-10** | B | template | `false` | `"desc"` | ≥2 match template+desc | `found` | ✅ | ❌ | ✅ | `[{p1},{p2}]` | |
| **Q-11** | C | template | `true` | _empty_ | _N/A_ | `fail` | ❌ | ❌ | ❌ | `{}` | |
| **Q-12** | C | template | `true` | `"desc"` | 0 match desc+template | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-12a** | C | template | `true` | `"desc"` | desc matches, template doesn't | `not_found` | ❌ | ❌ | ✅ | `{}` | |
| **Q-13** | C | template | `true` | `"desc"` | 1 exact match | `found` | ✅ | ❌ | ✅ | `[{policy}]` | |
| **Q-14** | C | template | `true` | `"desc"` | ≥2 exact matches | `found` | ✅ | ❌ | ✅ | `[{p1},{p2}]` | ⚠ non-unique desc |
| | | | | | | | | | | | |
| **V-1** | — | — | — | — | — | _module fail_ | — | — | ❌ | — | config missing |
| **V-2** | — | — | — | — | — | _module fail_ | — | — | ❌ | — | no switch |
| **V-3** | — | _any_ | `true` | dup desc+sw | — | _module fail_ | — | — | ❌ | — | dup desc |

---

## Playbook Examples for Each Case

### Q-1: Found by Policy ID
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    config:
      - name: POLICY-1234
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → found=true, DATA=[{policyId: POLICY-1234, ...}]
```

### Q-2: Policy ID Not Found
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    config:
      - name: POLICY-9999
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → found=false, DATA={}
```

### Q-3: Switch-Only (All Policies)
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    config:
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → found=true, DATA=[{all policies on switch}]
```

### Q-5 / Q-6 / Q-7: By Template Name (no desc filter)
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    config:
      - name: switch_freeform
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → found=true/false depending on whether policies exist
```

### Q-8 / Q-9: By Template Name + Description Filter
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    config:
      - name: switch_freeform
        description: "my-specific-policy"
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → found=true only if a switch_freeform policy with that exact description exists
```

### Q-11: desc_as_key=true with Empty Description (FAIL)
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    use_desc_as_key: true
    config:
      - name: switch_freeform
        # description intentionally omitted
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → FAIL: "description is required when use_desc_as_key=true"
```

### Q-12a: desc_as_key=true, Description Matches but Template Doesn't
```yaml
# Controller has: feature_enable policy with description "my-policy"
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    use_desc_as_key: true
    config:
      - name: switch_freeform          # ← looking for switch_freeform
        description: "my-policy"        # ← matches the feature_enable policy's desc
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → not_found (templateName post-filter removes the feature_enable match)
```

### Q-13: desc_as_key=true, Exact Match
```yaml
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    use_desc_as_key: true
    config:
      - name: switch_freeform
        description: "my-unique-desc"
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → found=true, DATA=[{the matching policy}]
```

### Q-14: desc_as_key=true, Multiple Matches (Warning)
```yaml
# Controller somehow has 2 switch_freeform policies with description "dup-desc"
- cisco.nd.nd_policy:
    fabric_name: my_fabric
    use_desc_as_key: true
    config:
      - name: switch_freeform
        description: "dup-desc"
      - switch:
          - serial_number: FDO29080NBU
    state: query
# → found=true, DATA=[{p1}, {p2}], WARNING: "Multiple policies (2) found..."
```

---

## Key Behavioral Notes

1. **Query is always read-only**: `changed` is always `false`. No API mutations occur.

2. **`use_desc_as_key` only matters when `name` is a template name**: If `name` is a policy ID (Case A) or omitted (Case D), the flag is completely ignored.

3. **Description as optional filter vs. required key**:
   - `use_desc_as_key=false` + description provided → description is an **optional post-filter** (Case B). Empty description is fine.
   - `use_desc_as_key=true` + description empty → **fail** (Case C/Q-11).

4. **Template post-filter in Case C is query-only**: When `use_desc_as_key=true`, the `templateName` post-filter only applies for `state=query`. For `merged`/`deleted`, the template mismatch is handled by diff logic (e.g., `delete_and_create`). This is intentional — see Bug 8 fix.

5. **Multiple config entries**: The playbook can have multiple policy entries in `config`. Each is processed independently through the full pipeline (`_build_want` → `_build_have` → `_get_diff_query_single` → `_execute_query`). One entry failing doesn't prevent others from being processed.

6. **Multi-switch expansion**: If the switch list has multiple switches, `_translate_config` expands each policy entry into one entry per switch. Each expanded entry goes through the query pipeline independently.

7. **Lucene tokenization caveat**: Lucene does tokenized matching (e.g., `description:my-policy` matches `my-policy-extended`). The code always post-filters for exact match to prevent false positives.
