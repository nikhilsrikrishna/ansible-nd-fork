# Merged State — Comprehensive Case Matrix

## Overview

The merged state is the module's **create/update/idempotency** mode for policies.
For each translated config entry, the module decides whether to:

- **Create** a new policy
- **Update** an existing policy in place
- **Skip** because the controller already matches the requested state
- **Replace** an existing policy by deleting it and creating a new one
- **Fail** the single entry because the request cannot be safely executed

Unlike `query`, merged state can modify controller state. Unlike `deleted`, it does
not batch all work into one bulk delete pass. Each config entry is processed individually,
and each entry can take a different action.

At a high level, merged state runs in four phases:

| Phase | Function | What It Does | Why It Matters |
|-------|----------|--------------|----------------|
| 1 | `_build_want()` | Translates playbook input into controller-style fields | Normalizes all entries into one consistent internal format |
| 1a | `_validate_template_inputs()` | Checks template input names, required parameters, and basic types | Catches obvious mistakes before create/update |
| 1b | `_build_have()` | Finds matching policies already on the controller | Supplies the existing state used for decision-making |
| 2 | `_get_diff_merged_single()` | Chooses `create`, `update`, `skip`, `delete_and_create`, or `fail` | This is the actual case matrix |
| 3 | `_execute_merged()` | Executes the chosen action per entry | Applies the change or records why nothing happened |
| 4 | `_deploy_policies()` | Optionally pushes changed policy IDs to switches | Makes controller-side changes take effect on devices |

> **Why merged is the most complex state:** it must be both safe and idempotent. The module
> has to avoid editing the wrong policy, avoid creating unnecessary duplicates when told not to,
> and still support precise updates when a unique identifier is available.

---

## Decision Factors

The merged-state outcome depends on these factors.

| # | Factor | Possible Values | Where Determined |
|---|--------|----------------|------------------|
| F1 | **`name`** | Policy ID (`POLICY-XXXX`) or template name (`switch_freeform`) | `config[].name` |
| F2 | **`use_desc_as_key`** | `true`, `false` | Top-level module parameter |
| F3 | **`description`** | Empty string or non-empty string | `config[].description` |
| F4 | **`create_additional_policy`** | `true`, `false` | `config[].create_additional_policy` |
| F5 | **Match count** | `0`, `1`, `>=2` | Result returned by `_build_have()` |
| F6 | **Field differences** | No diff, diff exists | Result of `_policies_differ()` |
| F7 | **Template match** | Same template, different template | Only relevant when `use_desc_as_key=true` |
| F8 | **`deploy`** | `true`, `false` | Top-level module parameter |
| F9 | **`check_mode`** | `true`, `false` | Ansible `--check` |

### Factor Dependencies

```text
name ──┬── POLICY-XXXX ───────────── direct, unique identifier
       │                              └── safe in-place update is possible
       │
       └── template_name ──┬── use_desc_as_key=false
                           │     └── template name is NOT unique
                           │     └── module never updates in place by template name alone
                           │
                           └── use_desc_as_key=true
                                 └── description becomes the unique key
                                 └── exact one match => update allowed
                                 └── different template => replace
                                 └── multiple matches => hard fail
```

---

## Validation Phase (Before the Action Decision)

Merged state has several validation layers. Some fail the **entire task immediately**.
Others mark only the current entry as failed and allow remaining entries to continue.

### Module-Level Validation in `main()`

These checks happen before `NDPolicyModule.manage_state()` starts processing entries.

| Check | Condition | Failure Type | Error Message / Meaning |
|-------|-----------|--------------|-------------------------|
| **V-1** | `config` missing or empty | Hard fail (`fail_json`) | `'config' element is mandatory for state 'merged'` |
| **V-2** | Any translated entry has no `name` | Hard fail (`fail_json`) | `config[N].name is required when state=merged.` |
| **V-3** | Any translated entry has `entity_type != switch` | Hard fail (`fail_json`) | Only `entity_type='switch'` supports merged state |
| **V-4** | Any translated entry has no `switch` after translation | Hard fail (`fail_json`) | Every policy entry must resolve to a switch serial number |

### `_validate_config()` Checks

These checks run before the module starts looking up controller state.

| Check | Condition | Applies When | Failure Type | Why It Exists |
|-------|-----------|-------------|--------------|---------------|
| **V-5** | Empty `description` while `use_desc_as_key=true` and `name` is a template name | `state in (merged, deleted)` | Hard fail (`fail_json`) | Description is required if it is the unique key |
| **V-6** | Duplicate `description + switch` pairs inside the playbook | `use_desc_as_key=true` | Hard fail (`fail_json`) | Prevents ambiguous updates within the same task |

> **Important:** V-5 and V-6 are intentionally atomic. If these checks fail, the task stops
> before any create or update API call is made.

### Per-Entry Template Validation in `_validate_template_inputs()`

This validation happens inside `_handle_merged_state()` **after** `_build_want()` and **before**
the controller lookup for that entry.

If validation fails, that entry is recorded as `action=fail`, but the module continues processing
other entries. This is a **soft fail per entry**, not a hard module abort.

| Check | What It Validates | Example Failure |
|-------|-------------------|-----------------|
| **V-7a** | Unknown template input keys | `Unknown templateInput key 'foo'` |
| **V-7b** | Missing required parameters with no default | `Required templateInput 'vrfName' is missing` |
| **V-7c** | Basic type format checks | `expects integer`, `expects boolean`, `expects IPv4 address` |

#### What `_validate_template_inputs()` Actually Does

1. Fetches the parameter schema for the template from the controller.
2. Caches that schema so repeated entries using the same template do not re-fetch it.
3. Ignores internal controller-managed parameters such as auto-populated values.
4. Validates only user-facing parameters.

#### Type Checks Covered

The helper performs lightweight checks for common parameter types:

- `boolean`
- `integer`
- `long`
- `float`
- `ipv4Address` / `ipAddress`
- `ipv4AddressWithSubnet`
- `macAddress`
- `enum` (against `validValues` when present)

> **Scope note:** this validation is intentionally lightweight. The controller remains the final
> authority. The module catches obvious mistakes early, but it does not try to fully re-implement
> server-side validation.

---

## How the Module Builds the Desired State (`_build_want`)

Each playbook entry is translated into a normalized internal dict named `want`.

For merged state, `want` contains:

- `switchId`
- either `policyId` or `templateName`
- `create_additional_policy`
- `entityType`
- `entityName`
- `description`
- `priority`
- `templateInputs`

Example translation:

```yaml
config:
  - name: switch_freeform
    switch: FDO12345ABC
    description: enable feature x
    priority: 700
    template_inputs:
      AAA: true
```

becomes internally:

```yaml
want:
  switchId: FDO12345ABC
  templateName: switch_freeform
  create_additional_policy: true
  entityType: switch
  entityName: SWITCH
  description: enable feature x
  priority: 700
  templateInputs:
    AAA: true
```

This normalized shape is what the diff logic evaluates.

---

## What Counts as a Difference (`_policies_differ`)

Merged state does **not** compare every field returned by the controller.
It compares only fields that matter for safe idempotent updates.

### Compared Fields

| Field | Comparison Rule | Why |
|-------|-----------------|-----|
| `description` | Exact string comparison | User-visible mutable field |
| `priority` | Numeric comparison | Mutable field |
| `templateInputs` | Only keys the user supplied are compared | Avoid false diffs from controller-injected fields |

### Template Input Comparison Rules

For `templateInputs`, the module:

1. Looks only at keys present in `want.templateInputs`
2. Converts both sides to `str()` before comparison
3. Ignores extra keys present only on the controller

This is very important because the controller may inject values such as fabric metadata,
policy metadata, or other internal fields that the user never asked to manage.

### Ignored Fields

These fields are treated as identity fields, system-managed fields, or intentionally
non-diff-driving fields:

- `policyId`
- `switchId`
- `templateName`
- `source`
- `entityType`
- `entityName`
- `createTimestamp`
- `updateTimestamp`
- `generatedConfig`
- `markDeleted`

> **Key behavioral implication:** if the user identifies a policy by template name only,
> the module will not update it in place even if only `description`, `priority`, or
> `templateInputs` differ. Template name alone is not unique enough for a safe update.

---

## Complete Case Matrix

### Legend

- **action**: internal decision chosen by `_get_diff_merged_single()`
- **found**: whether the controller lookup found a candidate policy
- **changed**: whether a real controller mutation happens (outside check mode)
- **Hard fail**: `module.fail_json()` immediately aborts the entire task
- **Soft fail**: result entry is recorded as failed, but other entries still run

---

### Group 1: Template Name Given, `use_desc_as_key=false` (Cases 1-6)

This is the safest but least specific mode.

The user identified the desired policy by **template name only**, which is **not unique**.
Multiple policies on the same switch can share the same template. Because of that, the module
**never updates in place** in this group. It either creates another policy or skips.

| Case | Match Count | Diff? | `create_additional_policy` | action | found | changed | Meaning |
|------|-------------|-------|----------------------------|--------|-------|---------|---------|
| **M-1** | `0` | N/A | `true` or `false` | `create` | ❌ | ✅ | No matching template policy exists, so create one |
| **M-2a** | `1` | No | `true` | `create` | ✅ | ✅ | Exact same policy exists, but duplicates are allowed |
| **M-2b** | `1` | No | `false` | `skip` | ✅ | ❌ | Exact same policy exists, and duplicates are not allowed |
| **M-3/4** | `1` | Yes | `true` or `false` | `create` | ✅ | ✅ | A similar policy exists, but template name alone is not safe for update |
| **M-5** | `>=2` | N/A | `true` | `create` | ✅ | ✅ | Multiple policies already use this template; still create another |
| **M-6** | `>=2` | N/A | `false` | `skip` | ✅ | ❌ | Multiple policies already exist and duplicates are disallowed |

#### Why Cases M-3/4 Create Instead of Update

This is the most important design rule in merged state:

> **A template name does not identify one unique policy.**

If the controller already has one `switch_freeform` policy and the user asks for another
`switch_freeform` policy with different inputs, the module cannot safely assume that the existing
one is the intended update target. It therefore creates a new policy instead of mutating the old one.

#### Role of `create_additional_policy`

This flag affects only the **no-diff / already-exists** scenarios in this group (and one similar
case in the policy-ID group). It answers the question:

- "If an identical policy already exists, should I create another copy anyway?"

If `true`, duplicates are allowed.
If `false`, the module behaves idempotently and skips.

---

### Group 2: Policy ID Given (Cases 7-11)

This is the most precise mode when `use_desc_as_key=false`.

Because a policy ID uniquely identifies a single controller object, the module **can safely update in place**.

| Case | Match Count | Diff? | `create_additional_policy` | action | found | changed | Meaning |
|------|-------------|-------|----------------------------|--------|-------|---------|---------|
| **M-7** | `0` | N/A | `true` or `false` | `skip` | ❌ | ❌ | Requested policy ID does not exist; module cannot create a policy with a chosen ID |
| **M-8a** | `1` | No | `true` | `create` | ✅ | ✅ | Matching policy exists and is identical, but user explicitly allows duplicate creation |
| **M-8b** | `1` | No | `false` | `skip` | ✅ | ❌ | Matching policy already matches desired state |
| **M-10/11** | `1` | Yes | `true` or `false` | `update` | ✅ | ✅ | Matching policy exists and differs; safe in-place update |

#### Special Behavior in M-8a

When the module decides to create a duplicate from a policy-ID-based request:

1. It removes `policyId` from `want`
2. It sends the request as a **create**, not an update

This matters because trying to create a new controller object while still carrying the original
`policyId` would fail with a uniqueness conflict.

#### Why M-7 Is a Skip, Not a Create

The controller assigns policy IDs. A playbook cannot say "create policy `POLICY-1234`".

So if the requested ID does not exist, the module reports a no-op with a warning-like error message:

> `Policy POLICY-1234 not found. Cannot create a policy with a specific ID.`

That keeps the behavior safe and honest.

---

### Group 3: `use_desc_as_key=true` (Cases 12-16)

In this mode, the module treats `description + switch` as the identity of a policy.

This enables update behavior without needing a policy ID, **but only if the description is truly unique**.

| Case | Match Count | Same Template? | Diff? | action | found | changed | Meaning |
|------|-------------|----------------|-------|--------|-------|---------|---------|
| **M-12** | `0` | N/A | N/A | `create` | ❌ | ✅ | No policy with that description exists on the switch |
| **M-13** | `1` | Yes | No | `skip` | ✅ | ❌ | Existing policy already matches desired state |
| **M-14** | `1` | Yes | Yes | `update` | ✅ | ✅ | Unique description identifies the exact policy to update |
| **M-15** | `1` | No | N/A | `delete_and_create` | ✅ | ✅ | Description matches, but template changed; replace the policy |
| **M-16** | `>=2` | N/A | N/A | Hard fail | ✅ | — | Multiple policies share the same description; update target is ambiguous |

#### Why M-15 Uses `delete_and_create`

If the controller finds exactly one policy by description, but that policy is built from a
**different template** than the one requested in the playbook, the module does not attempt
an in-place template swap.

Instead it:

1. Deletes the old policy
2. Creates a new policy from the requested template

This is safer because a template change is treated as a resource replacement, not as a small patch.

#### Why M-16 Is a Hard Fail

`use_desc_as_key=true` is only safe when one description identifies one policy per switch.
If the controller already contains duplicates, the module refuses to guess.

The task aborts with a message like:

> `Multiple policies (N) found with description 'X' on switch Y. Cannot determine which policy to update...`

This is intentionally strict because silently updating the wrong duplicate would be worse than failing.

---

## Execution Phase (`_execute_merged`)

Once the diff phase produces one result per config entry, `_execute_merged()` performs the actual work.

### Action Summary

| action | API Behavior | Result Type | Adds Policy ID For Deploy? |
|--------|--------------|-------------|----------------------------|
| `fail` | No API call | Failed result entry | No |
| `skip` | No API call | Successful no-op result | No |
| `create` | `POST` create policy | Created result entry | Yes, if create returns an ID |
| `update` | `PUT` update policy | Updated result entry | Yes |
| `delete_and_create` | Remove old policy, then create new one | Replacement result entry | Yes, new ID only |

### `fail`

This path is used for entry-specific problems such as template validation failure or lookup failure.

- The module records a failed result for that one entry
- It continues processing the remaining entries
- The final Ansible task is still marked failed because at least one sub-result failed

### `skip`

This is the idempotent no-op path.

- No controller mutation happens
- The result says `No changes needed`
- If the skip happened because a requested policy ID was missing, the diff payload carries the warning text

### `create`

Normal create behavior:

1. Build `PolicyCreate` payload
2. `POST` to the create endpoint
3. Parse the created policy ID from the response
4. Store that ID for optional later deploy

### `update`

Normal update behavior:

1. Build `PolicyUpdate` payload
2. `PUT` to the update endpoint for the specific policy ID
3. Add that policy ID to the deploy list

### `delete_and_create`

Replacement behavior:

1. Remove the old policy by ID
2. Attempt to create the new policy
3. If recreate succeeds, add the new ID to the deploy list
4. If recreate fails, the result records that the old policy was deleted but replacement failed

> **Operational note:** `delete_and_create` is not transactionally reversible. If the delete succeeds
> and the re-create fails, the old policy is gone. The module reports this accurately in the result.

---

## API Details That Affect Behavior

### Create API (`_api_create_policy`)

The create helper sends a `PolicyCreate` model containing:

- `switch_id`
- `template_name`
- `entity_type` (defaults to `switch`)
- `entity_name` (defaults to `SWITCH`)
- `description`
- `priority`
- `source`
- `template_inputs`

#### 207 Multi-Status Handling

The controller can return a `207 Multi-Status` style response where the HTTP request itself succeeds,
but the per-policy record contains `status="failed"`.

The helper detects that and raises `NDModuleError` so the entry is reported as a real failure.

This prevents false success when the controller accepted the request envelope but rejected the actual policy.

### Update API (`_api_update_policy`)

The update helper has one especially important behavior:

#### Template Inputs Are Merged, Not Replaced

Before sending the update payload, it does this:

1. Starts with the controller's existing `templateInputs`
2. Overlays only the keys provided by the user

That means a playbook can update only `description`, only `priority`, or only a subset of template inputs
without unintentionally wiping every other input currently stored on the policy.

Example:

```yaml
have.templateInputs:
  VLAN_ID: 100
  FABRIC_NAME: fab1
  MODE: trunk

want.templateInputs:
  MODE: access
```

Update payload contains:

```yaml
templateInputs:
  VLAN_ID: 100
  FABRIC_NAME: fab1
  MODE: access
```

This is a deliberate safety feature.

---

## Deploy Phase

After all entries are executed, `_handle_merged_state()` optionally deploys changed policies.

### When Deploy Happens

Deploy runs only if both conditions are true:

1. `deploy=true`
2. At least one policy ID was collected during create, update, or replacement

### What Gets Deployed

Only the policy IDs that were actually changed during this task:

- created IDs
- updated IDs
- replacement-created IDs

Skipped and failed entries do not contribute policy IDs.

### Deploy API Behavior

Deployment uses `pushConfig` with the list of changed policy IDs.

If `deploy=false`, the controller objects are still created/updated, but no push to switches occurs.

---

## Check Mode Behavior

Merged state supports check mode, but its behavior is worth calling out explicitly.

### What Happens in Check Mode

For `create`, `update`, and `delete_and_create`:

- The module records what **would** happen
- No controller mutation API calls are made
- No policy IDs are collected for deploy

### Important Consequence

Even if `deploy=true`, merged-state check mode does **not** produce a deploy action afterward,
because the execution phase never adds policy IDs to the deploy list in check mode.

So check mode accurately previews:

- which entries would be created
- which entries would be updated
- which entries would be replaced

but it does not simulate a final deploy pass.

---

## Idempotency Analysis

Merged state is idempotent in some paths and intentionally non-idempotent in others.

### Idempotent Paths

These produce `changed=false` on repeat runs:

- **M-2b**: identical template-based match exists and `create_additional_policy=false`
- **M-8b**: identical policy ID match exists and `create_additional_policy=false`
- **M-13**: identical unique-description match exists
- **M-7**: requested policy ID does not exist, so module skips

### Intentionally Non-Idempotent Paths

These can create duplicates on repeated runs:

- **M-2a**: exact match exists but duplicate creation is allowed
- **M-5**: multiple matches exist and duplicate creation is allowed
- **M-8a**: exact policy ID match exists but duplicate creation is allowed

### Conditionally Idempotent Paths

These converge once the requested state exists:

- **M-1** and **M-12**: first run creates, later runs usually skip/update depending on identifiers
- **M-10/11** and **M-14**: first run updates, later runs skip once fields match
- **M-15**: first run replaces, later runs skip or update depending on the new state

> **Practical advice:** if you want classic idempotent configuration management behavior,
> set `create_additional_policy=false` unless you intentionally want duplicates.

---

## Reader-Friendly Decision Flow

```text
START: one merged-state config entry
│
├─ V-1..V-6 hard validation passes?
│   └─ no → task aborts before controller mutation
│
├─ Build want dict
│
├─ Template input validation passes?
│   └─ no → entry gets action=fail, continue to next entry
│
├─ Find matching policies on controller
│
├─ Did user give a policy ID?
│   ├─ no match → M-7 skip
│   ├─ match + no diff + create_additional=true → M-8a create duplicate
│   ├─ match + no diff + create_additional=false → M-8b skip
│   └─ match + diff → M-10/11 update
│
├─ Else, is use_desc_as_key=true?
│   ├─ no matches → M-12 create
│   ├─ one match + same template + no diff → M-13 skip
│   ├─ one match + same template + diff → M-14 update
│   ├─ one match + different template → M-15 delete and create
│   └─ multiple matches → M-16 hard fail
│
└─ Else (template name only, use_desc_as_key=false)
    ├─ no matches → M-1 create
    ├─ one match + no diff + create_additional=true → M-2a create duplicate
    ├─ one match + no diff + create_additional=false → M-2b skip
    ├─ one match + diff → M-3/4 create new policy
    ├─ multiple matches + create_additional=true → M-5 create another
    └─ multiple matches + create_additional=false → M-6 skip
```

---

## Example Playbooks

### 1. Idempotent Create-or-Update by Unique Description

```yaml
- name: Manage policy by description
  cisco.nd.nd_policy:
    fabric_name: FAB1
    state: merged
    use_desc_as_key: true
    deploy: true
    config:
      - name: switch_freeform
        switch: FDO12345ABC
        description: enable telemetry
        priority: 500
        create_additional_policy: false
        template_inputs:
          TELEMETRY: true
```

Typical behavior:

- no existing description match → create (`M-12`)
- one exact match with same values → skip (`M-13`)
- one exact match with different values → update (`M-14`)

### 2. Precise Update by Policy ID

```yaml
- name: Update one known policy
  cisco.nd.nd_policy:
    fabric_name: FAB1
    state: merged
    config:
      - name: POLICY-123456
        switch: FDO12345ABC
        description: change priority only
        priority: 900
        create_additional_policy: false
```

Typical behavior:

- ID missing → skip (`M-7`)
- ID found and already matches → skip (`M-8b`)
- ID found but differs → update (`M-10/11`)

### 3. Template-Based Create Without In-Place Update

```yaml
- name: Create by template name only
  cisco.nd.nd_policy:
    fabric_name: FAB1
    state: merged
    use_desc_as_key: false
    config:
      - name: switch_freeform
        switch: FDO12345ABC
        description: another freeform policy
        create_additional_policy: false
        template_inputs:
          FEATURE_X: true
```

Typical behavior:

- no match → create (`M-1`)
- exact match exists → skip (`M-2b`)
- one different match exists → create new policy (`M-3/4`), not update

### 4. Template Replacement by Description Key

```yaml
- name: Replace policy when template changes
  cisco.nd.nd_policy:
    fabric_name: FAB1
    state: merged
    use_desc_as_key: true
    config:
      - name: feature_enable
        switch: FDO12345ABC
        description: uplink feature policy
        template_inputs:
          FEATURE: lacp
```

If the controller already has a policy on that switch with the same description but built from
another template, merged state chooses `delete_and_create` (`M-15`).

---

## Key Behavioral Notes

| Topic | Behavior |
|-------|----------|
| Template name only | Never updated in place because it is not a unique identifier |
| Policy ID | Safest way to perform an exact in-place update when `use_desc_as_key=false` |
| `use_desc_as_key=true` | Enables update-by-description, but only when descriptions are unique |
| Template change under description-key mode | Treated as replacement, not update |
| Template input updates | Merged on top of existing inputs, not wholesale replaced |
| Duplicate descriptions on controller | Cause hard failure in merged mode when description is used as the key |
| `create_additional_policy=true` | Allows deliberate duplicate creation even when an identical policy already exists |
| Check mode | Shows intended actions, but does not simulate deploy |

---

## Short Summary

If you want the most predictable merged-state behavior:

1. Use `use_desc_as_key=true` and give each policy a unique description per switch, **or**
2. Use a `POLICY-XXXX` ID when you need to update a specific existing policy, **and**
3. Set `create_additional_policy=false` unless you intentionally want duplicates

That combination gives the module enough identity to behave like classic idempotent configuration management
while still supporting safe create, update, and replacement workflows.
