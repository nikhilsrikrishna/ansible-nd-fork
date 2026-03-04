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
- Manages switch policies on Cisco Nexus Dashboard Fabric Controller (NDFC) 4.x.
- Supports creating, updating, deleting, querying, and deploying policies based on templates.
- Supports C(merged) state for idempotent policy management.
- Supports C(deleted) state for removing policies from NDFC and optionally from switches.
- Supports C(query) state for retrieving existing policy information.
- When O(use_desc_as_key=true), policies are identified by their description instead of policy ID.
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
    - List of policy configurations to manage.
    - Each entry describes a policy to create or update.
    type: list
    elements: dict
    required: true
    suboptions:
      name:
        description:
        - When the value starts with C(POLICY-), it is treated as a policy ID for direct lookup.
        - Otherwise, it is treated as a template name for creating or matching policies.
        - For C(query) and C(deleted) states, this is optional. When omitted, all policies on the specified switch are returned/deleted.
        type: str
      switch:
        description:
        - Serial number of the target switch (e.g., C(FDO25031SY4)).
        type: str
        required: true
        aliases: [ switch_id, serial_number ]
      description:
        description:
        - Description of the policy.
        - When O(use_desc_as_key=true), this is used as the unique identifier for the policy.
        type: str
        default: ""
      priority:
        description:
        - Priority of the policy.
        - Valid range is 1-2000.
        type: int
        default: 500
      entity_name:
        description:
        - Name of the entity the policy applies to.
        - Use C(SWITCH) for switch-level policies or an interface name (e.g., C(Ethernet1/1)) for interface policies.
        type: str
        default: SWITCH
      entity_type:
        description:
        - Type of entity the policy applies to.
        type: str
        choices: [ switch, configProfile, interface ]
        default: switch
      template_inputs:
        description:
        - Dictionary of name/value pairs passed to the policy template.
        - The required inputs depend on the template specified in O(config[].name).
        type: dict
        default: {}
  use_desc_as_key:
    description:
    - When set to V(true), the policy description is used as the unique key for matching.
    - When set to V(false), the template name (or policy ID if name starts with C(POLICY-)) is used.
    type: bool
    default: true
  create_additional_policy:
    description:
    - When set to V(true) and a matching policy already exists, a new duplicate policy is created.
    - When set to V(false) and a matching policy exists, the existing policy is updated (or skipped if identical).
    - Only relevant when O(use_desc_as_key=false) and the O(config[].name) is a template name.
    type: bool
    default: false
  deploy:
    description:
    - When set to V(true), policies are deployed to devices after create/update/delete operations.
    - For C(merged) state, this triggers a pushConfig action for the affected policy IDs.
    - For C(deleted) state, this triggers markDelete + pushConfig (to remove config from switches) before hard-deleting.
    type: bool
    default: false
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
    - Use C(deleted) to remove policies. When O(deploy=true), config is removed from switches first.
    - Use C(query) to retrieve existing policies without making changes.
    type: str
    choices: [ merged, deleted, query ]
    default: merged
extends_documentation_fragment:
- cisco.nd.modules
- cisco.nd.check_mode
"""

EXAMPLES = r"""
- name: Create a policy using template name
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    config:
      - name: feature_enable
        switch: FDO25031SY4
        description: "Enable LACP"
        template_inputs:
          featureName: lacp
    state: merged

- name: Create a policy and deploy it
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    config:
      - name: switch_freeform
        switch: FDO25031SY4
        description: "Custom config"
        template_inputs:
          CONF: |
            feature lacp
    deploy: true
    state: merged

- name: Update a policy by policy ID
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    use_desc_as_key: false
    config:
      - name: POLICY-121110
        switch: FDO25031SY4
        description: "Updated description"
        priority: 100
        template_inputs:
          featureName: lacp
    state: merged

- name: Use description as key to update
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    use_desc_as_key: true
    config:
      - name: feature_enable
        switch: FDO25031SY4
        description: "Enable LACP"
        priority: 100
        template_inputs:
          featureName: lacp
    state: merged

- name: Delete all policies with a template name
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    use_desc_as_key: false
    config:
      - name: feature_enable
        switch: FDO25031SY4
    deploy: true
    state: deleted

- name: Delete a specific policy by policy ID
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    config:
      - name: POLICY-121110
        switch: FDO25031SY4
    deploy: true
    state: deleted

- name: Delete policies by description
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    use_desc_as_key: true
    config:
      - name: feature_enable
        switch: FDO25031SY4
        description: "Enable LACP"
    deploy: true
    state: deleted

- name: Delete all policies on a switch
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    config:
      - switch: FDO25031SY4
    deploy: true
    state: deleted

- name: Delete policies without deploying (DB-only, config stays on switch)
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    use_desc_as_key: false
    config:
      - name: feature_enable
        switch: FDO25031SY4
    deploy: false
    state: deleted

- name: Query all policies on a switch
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    config:
      - switch: FDO25031SY4
    state: query

- name: Query policies by template name
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    use_desc_as_key: false
    config:
      - name: feature_enable
        switch: FDO25031SY4
    state: query

- name: Query a specific policy by policy ID
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    config:
      - name: POLICY-121110
        switch: FDO25031SY4
    state: query

- name: Query policies by description
  cisco.nd.nd_policy:
    fabric_name: my-fabric
    use_desc_as_key: true
    config:
      - name: feature_enable
        switch: FDO25031SY4
        description: "Enable LACP"
    state: query
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

import logging

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.cisco.nd.plugins.module_utils.log import Log
from ansible_collections.cisco.nd.plugins.module_utils.nd_policy_resources import NDPolicyModule
from ansible_collections.cisco.nd.plugins.module_utils.nd_v2 import (
    NDModule,
    NDModuleError,
    nd_argument_spec,
)
from ansible_collections.cisco.nd.plugins.module_utils.results import Results


# =============================================================================
# Main
# =============================================================================
def main():
    """Main entry point for the nd_policy module."""

    config_spec = dict(
        name=dict(type="str"),
        switch=dict(type="str", required=True, aliases=["switch_id", "serial_number"]),
        description=dict(type="str", default=""),
        priority=dict(type="int", default=500),
        entity_name=dict(type="str", default="SWITCH"),
        entity_type=dict(type="str", default="switch", choices=["switch", "configProfile", "interface"]),
        template_inputs=dict(type="dict", default={}),
    )

    argument_spec = nd_argument_spec()
    argument_spec.update(
        fabric_name=dict(type="str", required=True, aliases=["fabric"]),
        config=dict(type="list", elements="dict", required=True, options=config_spec),
        use_desc_as_key=dict(type="bool", default=True),
        create_additional_policy=dict(type="bool", default=False),
        deploy=dict(type="bool", default=False),
        ticket_id=dict(type="str"),
        cluster_name=dict(type="str"),
        state=dict(type="str", default="merged", choices=["merged", "deleted", "query"]),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
        required_if=[
            # name is required for merged state but optional for query
            ("state", "merged", ("config",)),
        ],
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
    output_level = module.params.get("output_level")

    # Validate: name is required for merged state
    if state == "merged":
        config = module.params.get("config")
        for idx, entry in enumerate(config):
            if not entry.get("name"):
                module.fail_json(
                    msg=f"config[{idx}].name is required when state=merged."
                )

    # Initialize Results
    results = Results()
    results.state = state
    results.check_mode = module.check_mode
    results.action = f"policy_{state}"

    try:
        log.info(f"Starting nd_policy module: state={state}")

        # Initialize NDModule (uses RestSend infrastructure internally)
        nd = NDModule(module)
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
        log.error(f"Unexpected error during module execution: {str(error)}")
        log.error(f"Error type: {type(error).__name__}")

        # Build failed result
        results.response_current = {
            "RETURN_CODE": -1,
            "MESSAGE": f"Unexpected error: {str(error)}",
            "DATA": {},
        }
        results.result_current = {"success": False, "found": False}
        results.diff_current = {}
        results.register_task_result()
        results.build_final_result()

        if output_level == "debug":
            import traceback
            results.final_result["traceback"] = traceback.format_exc()

        module.fail_json(msg=str(error), **results.final_result)


if __name__ == "__main__":
    main()
