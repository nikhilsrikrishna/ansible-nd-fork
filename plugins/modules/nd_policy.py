#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

ANSIBLE_METADATA = {"metadata_version": "1.1", "status": ["preview"], "supported_by": "community"}

DOCUMENTATION = r"""
---
module: nd_policy
version_added: "1.0.0"
short_description: Manages policies on Nexus Dashboard Fabric Controller (NDFC).
description:
- Supports creating, updating, deleting, querying, and deploying policies based on templates.
- Supports C(merged) state for idempotent policy management.
- Supports C(deleted) state for removing policies from NDFC and optionally from switches.
- Supports C(query) state for retrieving existing policy information.
- When O(use_desc_as_key=true), policies are identified by their description instead of policy ID.
- B(Atomic behavior) — the entire task is treated as a single transaction.
  If any validation check fails (e.g., missing or duplicate descriptions), the module
  aborts B(before) making any changes to the controller.
- When O(use_desc_as_key=true), every O(config[].description) B(must) be non-empty and
  unique per switch within the playbook. The module also fails if duplicate descriptions
  are found on the NDFC controller itself (created outside of this playbook). This ensures
  unambiguous policy matching. To manage policies with non-unique descriptions, use
  O(use_desc_as_key=false) and reference policies by policy ID.
- Policies and switches are specified separately in the O(config) list. Global policies
  apply to all switches listed in the C(switch) entry. Per-switch policy overrides can
  be specified using the C(policies) suboption inside each switch entry (only when
  O(use_desc_as_key=false)). Per-switch policies override global policies with the
  same template name for that switch.
- B(Update behavior) — when O(use_desc_as_key=false) and a template name is given,
  existing policies are never updated in-place. A new policy is always created. To update
  a specific policy, provide its policy ID (C(POLICY-xxxxx)) as the O(config[].name).
  When O(use_desc_as_key=true), the description uniquely identifies the policy, so
  in-place updates are supported.
author:
- L Nikhil Sri Krishna
options:
  fabric_name:
    description:
    - The name of the fabric containing the target switches.
    type: str
    required: true
    aliases: [ fabric ]
  config:
    description:
    - A list of dictionaries containing policy and switch information.
    - Policy entries define the template, description, priority, and template inputs.
    - A separate C(switch) entry lists the target switches and optional per-switch policy overrides.
    - All global policies (entries without C(switch) key) are applied to every switch listed
      in the C(switch) entry. Per-switch policies (specified under C(switch[].policies))
      override global policies with the same template name for that particular switch
      (only when O(use_desc_as_key=false); when O(use_desc_as_key=true) per-switch
      policies are simply merged with global policies).
    type: list
    elements: dict
    required: true
    suboptions:
      name:
        description:
        - This can be one of the following.
        - B(Template Name) — a name identifying the template (e.g., C(switch_freeform), C(feature_enable)).
          Note that a template name can be used by multiple policies and hence does not identify a policy uniquely.
        - B(Policy ID) — a unique ID identifying a policy (e.g., C(POLICY-121110)).
          Policy ID B(must) be used for modifying existing policies when O(use_desc_as_key=false),
          since template names cannot uniquely identify a policy.
        - For C(query) and C(deleted) states, this is optional. When omitted, all policies
          on the specified switch are returned/deleted.
        type: str
      description:
        description:
        - Description of the policy.
        - When O(use_desc_as_key=true), this is used as the unique identifier for the policy
          and B(must) be non-empty and unique per switch. The module fails atomically if
          duplicate descriptions are detected in the playbook or on the NDFC controller.
        type: str
        default: ""
      priority:
        description:
        - Priority of the policy.
        - Valid range is 1-2000.
        type: int
        default: 500
      create_additional_policy:
        description:
        - A flag indicating if a policy is to be created even if an identical policy already exists.
        - When set to V(true), a new duplicate policy is created regardless of whether a matching one exists.
        - When set to V(false), duplicate creation is skipped if an identical policy already exists.
        - Only relevant when O(use_desc_as_key=false) and O(config[].name) is a template name.
        type: bool
        default: true
      entity_name:
        description:
        - Name of the entity the policy applies to.
        - Use C(SWITCH) for switch-level policies or an interface name (e.g., C(Ethernet1/1)) for interface policies.
        type: str
        default: SWITCH
      entity_type:
        description:
        - Type of entity the policy applies to.
        - Only V(switch) is supported with C(merged) state. For V(configProfile) and V(interface),
          only C(query) and C(deleted) states are allowed.
        type: str
        choices: [ switch, configProfile, interface ]
        default: switch
      template_inputs:
        description:
        - Dictionary of name/value pairs passed to the policy template.
        - The required inputs depend on the template specified in O(config[].name).
        type: dict
        default: {}
      switch:
        description:
        - A list of switches and optional per-switch policy overrides.
        - All switches in this list will be deployed with the global policies defined
          at the top level of O(config). Per-switch policy overrides can be specified
          using the C(policies) suboption.
        type: list
        elements: dict
        suboptions:
          serial_number:
            description:
            - Serial number of the target switch (e.g., C(FDO25031SY4)).
            - The alias C(ip) is kept for backward compatibility and may be a
              switch management IP or hostname. The module resolves that value
              to the switch serial number before calling policy APIs.
            type: str
            required: true
            aliases: [ ip ]
          policies:
            description:
            - A list of policies specific to this switch that override global policies
              with the same template name (when O(use_desc_as_key=false)).
            - When O(use_desc_as_key=true), per-switch policies are simply merged with
              global policies rather than overriding by template name.
            type: list
            elements: dict
            default: []
            suboptions:
              name:
                description:
                - Template name or policy ID, same semantics as the top-level O(config[].name).
                type: str
                required: true
              description:
                description:
                - Description of the policy.
                type: str
                default: ""
              priority:
                description:
                - Priority of the policy.
                type: int
                default: 500
              create_additional_policy:
                description:
                - A flag indicating if a policy is to be created even if an identical policy already exists.
                type: bool
                default: true
              template_inputs:
                description:
                - Dictionary of name/value pairs passed to the policy template.
                type: dict
                default: {}
  use_desc_as_key:
    description:
    - When set to V(true), the policy description is used as the unique key for matching.
    - When set to V(false), the template name (or policy ID if name starts with C(POLICY-)) is used.
    - When V(true), every O(config[].description) must be non-empty (for C(merged) and C(deleted) states)
      and unique per switch within the playbook. The module will B(fail immediately) if duplicate
      C(description + switch) combinations are found in the playbook config or on the NDFC controller.
    - This atomic-fail behavior ensures no partial changes are made when descriptions are ambiguous.
    type: bool
    default: false
  deploy:
    description:
    - When set to V(true), policies are deployed to devices after create/update/delete operations.
    - For C(merged) state, this triggers a pushConfig action for the affected policy IDs.
    - For C(deleted) state, this triggers C(markDelete) → C(pushConfig) → C(remove) to remove
      config from switches and then hard-delete the policy records from the controller.
    - For C(deleted) with O(deploy=false), only C(markDelete) is performed on the controller.
      Policy records remain marked for deletion (with negative priority) until a subsequent
      run with O(deploy=true) or manual intervention.
    - B(Exception) — C(switch_freeform) policies are always deleted via a direct C(DELETE)
      API call regardless of the O(deploy) setting, because the C(markDelete) operation
      is not supported for this template.
    type: bool
    default: true
  ticket_id:
    description:
    - Change Control Ticket ID to associate with mutation operations.
    - Required when Change Control is enabled on the NDFC controller.
    type: str
  cluster_name:
    description:
    - Target cluster name in a multi-cluster deployment.
    type: str
  state:
    description:
    - Use C(merged) to create or update policies.
    - Use C(deleted) to delete policies.
    - For C(deleted) with O(deploy=true), the module performs
      C(markDelete) → C(pushConfig) → C(remove).
    - For C(deleted) with O(deploy=false), only C(markDelete) is performed on the controller.
      Policy records remain marked for deletion (with negative priority) until a subsequent
      run with O(deploy=true) or manual intervention.
    - B(Exception) — C(switch_freeform) policies skip the C(markDelete) flow entirely
      and are removed via a direct C(DELETE) API call regardless of the O(deploy) setting.
    - Use C(query) to retrieve existing policies without making changes.
    type: str
    choices: [ merged, deleted, query ]
    default: merged
extends_documentation_fragment:
- cisco.nd.modules
- cisco.nd.check_mode
seealso:
- name: Cisco NDFC Policy Management
  description: Understanding switch policy management on NDFC 4.x.
notes:
- When O(use_desc_as_key=false) and O(config[].name) is a template name (not a policy ID),
  existing policies are B(never) updated in-place. The module always creates a new policy.
  This is because multiple policies can share the same template name, making it ambiguous
  which policy to update. To update a specific policy, use its policy ID (C(POLICY-xxxxx)).
- When O(use_desc_as_key=true), the description uniquely identifies the policy per switch,
  so in-place updates B(are) supported. If the template name changes, the old policy is
  deleted and a new one is created.
- C(switch_freeform) policies do not support the C(markDelete) API. They are always
  removed via a direct C(DELETE) API call, regardless of the O(deploy) setting.
- If C(pushConfig) fails during a C(deleted) operation (e.g., switch unreachable), the
  module aborts before the final C(remove) step. Policies remain in a C(markDeleted) state
  with negative priority. Re-run the task after fixing connectivity to complete the deletion.
  If a C(merged) task is run while stale C(markDeleted) policies exist, the module
  automatically cleans them up.
"""

EXAMPLES = r"""
# NOTE: In the following create task, policies template_101, template_102, and template_103
#       are deployed on switch2, whereas policies template_104 and template_105 are the only
#       policies installed on switch1 (per-switch override).

- name: Create different policies with per-switch overrides
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: merged
    deploy: true
    config:
      - name: template_101
        create_additional_policy: false
        priority: 101

      - name: template_102
        create_additional_policy: false
        description: "102 - No priority given"

      - name: template_103
        create_additional_policy: false
        description: "Both description and priority given"
        priority: 500

      - switch:
          - serial_number: "{{ switch1 }}"
            policies:
              - name: template_104
                create_additional_policy: false
              - name: template_105
                create_additional_policy: false
          - serial_number: "{{ switch2 }}"

# CREATE POLICY (including template inputs)

- name: Create policy including required template inputs
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    config:
      - name: switch_freeform
        create_additional_policy: false
        priority: 101
        template_inputs:
          CONF: |
            feature lacp

      - switch:
          - serial_number: "{{ switch1 }}"

# MODIFY POLICY (using policy ID)

# NOTE: Since there can be multiple policies with the same template name, policy-id MUST be used
#       to modify a particular policy when use_desc_as_key is false.

- name: Modify policies using policy IDs
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: merged
    deploy: true
    config:
      - name: POLICY-101101
        create_additional_policy: false
        priority: 101

      - name: POLICY-102102
        create_additional_policy: false
        description: "Updated description"

      - switch:
          - serial_number: "{{ switch1 }}"

# UPDATE using description as key

- name: Use description as key to update
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    use_desc_as_key: true
    config:
      - name: feature_enable
        description: "Enable LACP"
        priority: 100
        template_inputs:
          featureName: lacp

      - switch:
          - serial_number: "{{ switch1 }}"
    state: merged

# Use description as key with per-switch policies

- name: Create policies with description as key
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    use_desc_as_key: true
    config:
      - name: switch_freeform
        create_additional_policy: false
        description: "policy_radius"
        template_inputs:
          CONF: |
            radius-server host 10.1.1.2 key 7 "ljw3976!" authentication accounting
      - switch:
          - serial_number: "{{ switch1 }}"
            policies:
              - name: switch_freeform
                create_additional_policy: false
                priority: 101
                description: "feature bfd"
                template_inputs:
                  CONF: |
                    feature bfd
              - name: switch_freeform
                create_additional_policy: false
                priority: 102
                description: "feature bash-shell"
                template_inputs:
                  CONF: |
                    feature bash-shell
          - serial_number: "{{ switch2 }}"
          - serial_number: "{{ switch3 }}"

# DELETE POLICY

- name: Delete policies using template name
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: deleted
    config:
      - name: template_101
      - name: template_102
      - name: template_103
      - switch:
          - serial_number: "{{ switch1 }}"
          - serial_number: "{{ switch2 }}"

- name: Delete policies using policy-id
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: deleted
    config:
      - name: POLICY-101101
      - name: POLICY-102102
      - switch:
          - serial_number: "{{ switch1 }}"

- name: Delete all policies on switches
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: deleted
    config:
      - switch:
          - serial_number: "{{ switch1 }}"
          - serial_number: "{{ switch2 }}"

- name: Delete policies without deploying (mark for deletion only)
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: deleted
    deploy: false
    config:
      - name: template_101
      - switch:
          - serial_number: "{{ switch1 }}"

# NOTE: switch_freeform policies are always directly deleted
#       regardless of the deploy setting.

- name: Delete switch_freeform policies (direct DELETE)
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: deleted
    config:
      - name: switch_freeform
      - switch:
          - serial_number: "{{ switch1 }}"

- name: Delete policies using description as key
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    use_desc_as_key: true
    state: deleted
    config:
      - name: switch_freeform
        description: "Enable LACP"
      - switch:
          - serial_number: "{{ switch1 }}"

# QUERY

- name: Query all policies from specified switches
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: query
    config:
      - switch:
          - serial_number: "{{ switch1 }}"
          - serial_number: "{{ switch2 }}"

- name: Query policies matching template names
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: query
    config:
      - name: template_101
      - name: template_102
      - switch:
          - serial_number: "{{ switch1 }}"

- name: Query policies using policy-ids
  cisco.nd.nd_policy:
    fabric_name: "{{ fabric_name }}"
    state: query
    config:
      - name: POLICY-101101
      - name: POLICY-102102
      - switch:
          - serial_number: "{{ switch1 }}"
"""

RETURN = r"""
changed:
  description: Whether any changes were made.
  returned: always
  type: bool
  sample: false
failed:
  description: Whether the operation failed.
  returned: always
  type: bool
  sample: false
before:
  description:
  - List of policy snapshots B(before) the module made any changes.
  - For C(merged) state, contains the existing policy state prior to create/update.
  - For C(deleted) state, contains the policies that were deleted.
  - For C(query) state, this is an empty list.
  returned: always
  type: list
  elements: dict
after:
  description:
  - List of policy snapshots B(after) the module completed.
  - For C(merged) state, contains the new/updated policy state.
  - For C(deleted) state, this is an empty list (policies were removed).
  - For C(query) state, contains the queried policies.
  returned: always
  type: list
  elements: dict
proposed:
  description:
  - List of proposed policy changes derived from the playbook config.
  - Only returned when O(output_level) is set to V(info) or V(debug).
  returned: when output_level is info or debug
  type: list
  elements: dict
diff:
  description: List of differences between desired and existing state.
  returned: always
  type: list
  elements: dict
response:
  description: List of controller responses.
  returned: always
  type: list
  elements: dict
result:
  description: List of operation results.
  returned: always
  type: list
  elements: dict
metadata:
  description: List of operation metadata.
  returned: always
  type: list
  elements: dict
"""

import copy
import logging

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.nd.plugins.module_utils.common.log import Log
from ansible_collections.cisco.nd.plugins.module_utils.endpoints.v1.base_paths_manage import BasePath
from ansible_collections.cisco.nd.plugins.module_utils.nd_policy_resources import NDPolicyModule
from ansible_collections.cisco.nd.plugins.module_utils.nd_v2 import (
    NDModule,
    NDModuleError,
    nd_argument_spec,
)
from ansible_collections.cisco.nd.plugins.module_utils.rest.results import Results


# =============================================================================
# Config Translation
# =============================================================================
def _translate_config(config, use_desc_as_key):
    """Translate the playbook config into a flat list of per-switch policy dicts.

    The playbook config uses a two-level structure:
        - Global policy entries: dicts with ``name``, ``description``, etc.
        - A switch entry: a dict with ``switch`` key containing a list of
          switch dicts, each with ``serial_number`` and optional ``policies``.

    This function:
        1. Pops the switch entry from the config.
        2. For each switch, adds its serial number to every global policy.
        3. If a switch has per-switch ``policies``, those override (by template
           name) the global policies for that switch (when
           ``use_desc_as_key=false``).  When ``use_desc_as_key=true``,
           per-switch policies are simply merged with global policies.
        4. Returns a flat list where each dict has a ``switch`` key with a
           single serial number string.

    Args:
        config: The raw config list from the playbook (will be mutated).
        use_desc_as_key: Whether descriptions are used as unique keys.

    Returns:
        Flat list of policy dicts, each with a ``switch`` (serial number) key.
    """
    if config is None:
        return []

    # Find the switch entry (the dict that has a "switch" key containing a list)
    pos = next(
        (index for index, d in enumerate(config) if "switch" in d and isinstance(d["switch"], list)),
        None,
    )

    if pos is None:
        # No switch entry found — config is already flat (each entry has its own switch)
        return config

    sw_dict = config.pop(pos)
    global_policies = config  # Remaining entries are global policies

    override_config = []
    for sw in sw_dict["switch"]:
        sn = sw.get("serial_number") or sw.get("ip", "")

        # Collect per-switch policy overrides
        if sw.get("policies"):
            for pol in sw["policies"]:
                entry = copy.deepcopy(pol)
                entry["switch"] = sn
                override_config.append(entry)

        # Add this switch to every global policy
        for cfg in global_policies:
            if "switch" not in cfg or not isinstance(cfg["switch"], list):
                if "switch" not in cfg or cfg["switch"] is None:
                    cfg["switch"] = []
                elif isinstance(cfg["switch"], str):
                    cfg["switch"] = [cfg["switch"]]
            if sn not in cfg["switch"]:
                cfg["switch"].append(sn)

    # Switch-only: no global policies AND no per-switch overrides → generate
    # a bare entry per switch so downstream can handle Case D (all policies
    # on switch) for query/deleted states.
    if not global_policies and not override_config:
        return [{"switch": sw.get("serial_number") or sw.get("ip", "")} for sw in sw_dict["switch"]]

    # Now flatten: when use_desc_as_key is false, per-switch policies override
    # global policies with the same template name for that switch.
    if global_policies and not use_desc_as_key:
        updated_config = []
        for ovr_cfg in override_config:
            for cfg in global_policies:
                if cfg.get("name") == ovr_cfg.get("name"):
                    # Remove the override switch from the global policy's switch list
                    ovr_sw = ovr_cfg["switch"]
                    if isinstance(cfg.get("switch"), list) and ovr_sw in cfg["switch"]:
                        cfg["switch"].remove(ovr_sw)
            if ovr_cfg not in updated_config:
                updated_config.append(ovr_cfg)
        # Add global policies that still have switches assigned
        for cfg in global_policies:
            if isinstance(cfg.get("switch"), list) and cfg["switch"]:
                updated_config.append(cfg)
        flat_config = updated_config
    else:
        # use_desc_as_key=true: per-switch policies are simply merged
        flat_config = list(global_policies) + override_config

    # Final step: expand multi-switch global policies into one entry per switch
    result = []
    for cfg in flat_config:
        if isinstance(cfg.get("switch"), list):
            for sw in cfg["switch"]:
                entry = copy.deepcopy(cfg)
                entry["switch"] = sw
                result.append(entry)
        else:
            # Already has a single switch string
            result.append(cfg)

    return result


def _looks_like_ip(value):
    """Return True if value looks like an IPv4 address (simple heuristic)."""
    parts = value.split(".")
    if len(parts) == 4:
        return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
    return False


def _needs_resolution(value):
    """Return True if the switch identifier needs IP/hostname-to-serial resolution.

    Serial numbers are alphanumeric strings (e.g. FDO25031SY4).
    IPs look like dotted quads.  Hostnames contain dots or look like FQDNs.
    If the value is already a serial number we can skip the fabric API call.
    """
    if not value:
        return False
    v = str(value).strip()
    # IPv4 address
    if _looks_like_ip(v):
        return True
    # Hostname / FQDN (contains a dot but isn't an IP)
    if "." in v:
        return True
    return False


def _query_fabric_switches(nd, fabric_name):
    """Query all switches for a fabric and return raw switch records.

    Uses RestSend save_settings/restore_settings to temporarily force
    check_mode=False so that this read-only GET always hits the controller,
    even when the module is running in Ansible check mode.
    """
    path = f"{BasePath.nd_manage_fabrics(fabric_name, 'switches')}?max=10000"

    # Temporarily disable check_mode for this read-only lookup so the
    # controller is queried even when Ansible runs with --check.
    rest_send = nd._get_rest_send()
    rest_send.save_settings()
    rest_send.check_mode = False
    try:
        response = nd.request(path)
    finally:
        rest_send.restore_settings()

    if isinstance(response, list):
        return response
    if isinstance(response, dict):
        return response.get("switches", [])
    return []


def _translate_switch_identifiers(config, nd, fabric_name, module):
    """Resolve switch IP/hostname inputs to policy API serial numbers.

    The user's arg-spec field is ``serial_number`` with alias ``ip``.
    Ansible normalises both into ``serial_number``.  After
    ``_translate_config`` the value lives in ``entry["switch"]`` as a
    plain string.

    Resolution logic:
        1. If the value does NOT look like an IP or hostname it is
           assumed to be a serial number already → pass through as-is.
        2. If the value looks like an IP or hostname, query the fabric
           switch inventory and resolve it to a serial number.
        3. If resolution fails, raise a clear error.
    """
    if config is None:
        return []

    # Collect unique identifiers that actually need resolution
    needs_lookup = set()
    for entry in config:
        switch_value = entry.get("switch")
        if isinstance(switch_value, list):
            for switch_entry in switch_value:
                val = switch_entry.get("serial_number") or switch_entry.get("ip") or ""
                if _needs_resolution(val):
                    needs_lookup.add(val)
        elif isinstance(switch_value, str) and _needs_resolution(switch_value):
            needs_lookup.add(switch_value)

    # Only call the fabric API if there are identifiers to resolve
    if not needs_lookup:
        return config

    switches = _query_fabric_switches(nd, fabric_name)

    ip_map = {}
    hostname_map = {}

    for switch in switches:
        switch_id = switch.get("switchId") or switch.get("serialNumber")
        if not switch_id:
            continue

        fabric_ip = switch.get("fabricManagementIp") or switch.get("ip")
        if fabric_ip:
            ip_map[str(fabric_ip).strip()] = switch_id

        hostname = switch.get("hostname")
        if hostname:
            hostname_map[str(hostname).strip().lower()] = switch_id

    def resolve(identifier):
        if identifier is None:
            return None
        value = str(identifier).strip()
        if not value:
            return value
        # Try IP map first, then hostname map
        return ip_map.get(value) or hostname_map.get(value.lower())

    for entry in config:
        switch_value = entry.get("switch")

        if isinstance(switch_value, list):
            for switch_entry in switch_value:
                original = switch_entry.get("serial_number") or switch_entry.get("ip")
                if not _needs_resolution(original):
                    continue  # Already a serial number — leave it alone
                resolved = resolve(original)
                if resolved is None:
                    module.fail_json(
                        msg=(
                            f"Unable to resolve switch identifier '{original}' to a serial number "
                            f"in fabric '{fabric_name}'. Provide a valid switch serial_number, "
                            "management IP, or hostname from the fabric inventory."
                        )
                    )
                switch_entry["serial_number"] = resolved
                if "ip" in switch_entry:
                    switch_entry["ip"] = resolved
        elif isinstance(switch_value, str):
            if not _needs_resolution(switch_value):
                continue  # Already a serial number — leave it alone
            resolved = resolve(switch_value)
            if resolved is None:
                module.fail_json(
                    msg=(
                        f"Unable to resolve switch identifier '{switch_value}' to a serial number "
                        f"in fabric '{fabric_name}'. Provide a valid switch serial_number, "
                        "management IP, or hostname from the fabric inventory."
                    )
                )
            entry["switch"] = resolved

    return config


# =============================================================================
# Main
# =============================================================================
def main():
    """Main entry point for the nd_policy module."""

    # Per-switch policy suboptions (used inside switch[].policies)
    switch_policy_spec = dict(
        name=dict(type="str", required=True),
        description=dict(type="str", default=""),
        priority=dict(type="int", default=500),
        create_additional_policy=dict(type="bool", default=True),
        template_inputs=dict(type="dict", default={}),
    )

    # Switch list suboptions
    switch_spec = dict(
        serial_number=dict(type="str", required=True, aliases=["ip"]),
        policies=dict(type="list", elements="dict", default=[], options=switch_policy_spec),
    )

    # Top-level config entry suboptions
    config_spec = dict(
        name=dict(type="str"),
        description=dict(type="str", default=""),
        priority=dict(type="int", default=500),
        create_additional_policy=dict(type="bool", default=True),
        entity_name=dict(type="str", default="SWITCH"),
        entity_type=dict(type="str", default="switch", choices=["switch", "configProfile", "interface"]),
        template_inputs=dict(type="dict", default={}),
        switch=dict(type="list", elements="dict", options=switch_spec),
    )

    argument_spec = nd_argument_spec()
    argument_spec.update(
        fabric_name=dict(type="str", required=True, aliases=["fabric"]),
        config=dict(type="list", elements="dict", required=True, options=config_spec),
        use_desc_as_key=dict(type="bool", default=False),
        deploy=dict(type="bool", default=True),
        ticket_id=dict(type="str"),
        cluster_name=dict(type="str"),
        state=dict(type="str", default="merged", choices=["merged", "deleted", "query"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    # Initialize logging
    try:
        log_config = Log()
        log_config.commit()
        log = logging.getLogger("nd.nd_policy")
    except ValueError as error:
        module.fail_json(msg=str(error))

    # Get parameters
    state = module.params.get("state")
    use_desc_as_key = module.params.get("use_desc_as_key")
    output_level = module.params.get("output_level")
    fabric_name = module.params.get("fabric_name")

    if not module.params.get("config"):
        module.fail_json(
            msg=f"'config' element is mandatory for state '{state}'."
        )

    try:
        nd = NDModule(module)
    except Exception as error:
        module.fail_json(msg=f"Failed to initialize NDModule: {str(error)}")

    try:
        translated_input = _translate_switch_identifiers(
            copy.deepcopy(module.params["config"]),
            nd,
            fabric_name,
            module,
        )
    except NDModuleError as error:
        module.fail_json(
            msg=(
                f"Failed to resolve switch identifiers for fabric '{fabric_name}': "
                f"{error.msg}"
            )
        )

    # Translate the playbook config: flatten multi-switch structure into
    # one entry per (policy, switch) pair, applying per-switch overrides.
    # This must happen before any state handling so the downstream code
    # operates on a uniform flat list.
    translated_config = _translate_config(
        translated_input,
        use_desc_as_key,
    )

    # Validate: name is required for merged state
    if state == "merged":
        for idx, entry in enumerate(translated_config):
            if not entry.get("name"):
                module.fail_json(
                    msg=f"config[{idx}].name is required when state=merged."
                )

    # Validate: merged state is only supported for entity_type=switch
    if state == "merged":
        for idx, entry in enumerate(translated_config):
            entity_type = entry.get("entity_type", "switch")
            if entity_type != "switch":
                module.fail_json(
                    msg=(
                        f"config[{idx}]: entity_type='{entity_type}' is not supported "
                        f"with state=merged. Only entity_type='switch' supports merged state. "
                        f"Use state=query or state=deleted for entity_type='{entity_type}'."
                    )
                )

    # Validate: every translated entry must have a switch
    for idx, entry in enumerate(translated_config):
        if not entry.get("switch"):
            module.fail_json(
                msg=f"config[{idx}]: every policy entry must have a switch serial number after translation."
            )

    # Override module.params["config"] with the translated flat config
    # so that NDPolicyModule sees the uniform structure.
    module.params["config"] = translated_config

    # Initialize Results
    results = Results()
    results.state = state
    results.check_mode = module.check_mode
    results.action = f"policy_{state}"

    try:
        log.info(f"Starting nd_policy module: state={state}")

        log.info("NDModule initialized successfully")

        # Create NDPolicyModule
        policy_module = NDPolicyModule(
            nd=nd,
            results=results,
            logger=log,
        )
        log.info("NDPolicyModule initialized successfully")

        # Manage state for merged, query, deleted
        log.info(f"Managing state: {state}")
        policy_module.manage_state()

        # Exit with results
        log.info(f"State management completed successfully. Changed: {results.changed}")
        policy_module.exit_json()

    except NDModuleError as error:
        # NDModule-specific errors (API failures, authentication issues, etc.)
        log.error(f"NDModule error: {error.msg}")

        # Try to get response from RestSend if available
        try:
            results.response_current = nd.rest_send.response_current
            results.result_current = nd.rest_send.result_current
        except (AttributeError, ValueError):
            # Fallback if RestSend wasn't initialized or no response available
            results.response_current = {
                "RETURN_CODE": error.status if error.status else -1,
                "MESSAGE": error.msg,
                "DATA": error.response_payload if error.response_payload else {},
            }
            results.result_current = {"success": False, "found": False}

        results.diff_current = {}
        results.register_task_result()
        results.build_final_result()

        # Add error details if debug output is requested
        if output_level == "debug":
            results.final_result["error_details"] = error.to_dict()

        log.error(f"Module failed: {results.final_result}")
        module.fail_json(msg=error.msg, **results.final_result)

    except Exception as error:
        # Unexpected errors
        import traceback
        tb_str = traceback.format_exc()

        log.error(f"Unexpected error during module execution: {str(error)}")
        log.error(f"Error type: {type(error).__name__}")

        # Build failed result — wrapped in its own try/except to avoid
        # masking the original error if Results operations fail.
        try:
            results.response_current = {
                "RETURN_CODE": -1,
                "MESSAGE": f"Unexpected error: {str(error)}",
                "DATA": {},
            }
            results.result_current = {"success": False, "found": False}
            results.diff_current = {}
            results.register_task_result()
            results.build_final_result()

            fail_kwargs = results.final_result
        except Exception:
            fail_kwargs = {}

        if output_level == "debug":
            fail_kwargs["traceback"] = tb_str

        module.fail_json(msg=f"{type(error).__name__}: {str(error)}", **fail_kwargs)


if __name__ == "__main__":
    main()
