# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
ND Policy Resource Module.

Provides all business logic for switch policy management on NDFC 4.x:
    - Policy CRUD (create, read, update, delete)
    - Idempotency diff calculation for merged, query, deleted states
    - Deploy (pushConfig) orchestration
    - Bulk markDelete → pushConfig → remove delete flow

The module file ``nd_policy.py`` contains only DOCUMENTATION, argument_spec,
and a thin ``main()`` that instantiates this class and calls ``manage_state()``.

Models (from ``models.policy``):
    - ``PolicyCreate``      – single policy create payload
    - ``PolicyCreateBulk``  – bulk policy create wrapper
    - ``PolicyUpdate``      – policy update payload (extends PolicyCreate)
    - ``PolicyIds``         – list of policy IDs for actions
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from ansible_collections.cisco.nd.plugins.module_utils.enums import OperationType
from ansible_collections.cisco.nd.plugins.module_utils.ep.ep_api_v1_manage_config_templates import (
    EpApiV1ManageConfigTemplatesGet,
)
from ansible_collections.cisco.nd.plugins.module_utils.ep.ep_api_v1_manage_policies import (
    EpApiV1ManagePoliciesGet,
    EpApiV1ManagePoliciesPost,
    EpApiV1ManagePoliciesPut,
    EpApiV1ManagePolicyActionsMarkDelete,
    EpApiV1ManagePolicyActionsPushConfig,
    EpApiV1ManagePolicyActionsRemove,
)
from ansible_collections.cisco.nd.plugins.module_utils.models.policy import (
    PolicyCreate,
    PolicyCreateBulk,
    PolicyIds,
    PolicyUpdate,
)
from ansible_collections.cisco.nd.plugins.module_utils.nd_v2 import (
    NDModule,
    NDModuleError,
)
from ansible_collections.cisco.nd.plugins.module_utils.results import Results


class NDPolicyModule:
    """Specialized module for switch policy lifecycle management.

    Provides policy-specific operations on top of NDModule:
        - Query and match existing policies (Lucene + post-filtering)
        - Idempotent diff calculation across 16 merged / 13 query / 16 deleted cases
        - Create, update, delete_and_create actions
        - Bulk deploy via pushConfig
        - 3-step delete flow: markDelete → pushConfig → remove

    Schema models (from ``models.policy``):
        - ``PolicyCreate``      – single policy create request body
        - ``PolicyCreateBulk``  – bulk create wrapper
        - ``PolicyUpdate``      – update request body (extends PolicyCreate)
        - ``PolicyIds``         – list of policy IDs for bulk actions
    """

    # =========================================================================
    # Initialization & Lifecycle
    # =========================================================================

    def __init__(
        self,
        nd: NDModule,
        results: Results,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the Policy Resource Module.

        Args:
            nd:      NDModule instance (wraps the Ansible module and REST client).
            results: Results aggregation instance for task output.
            logger:  Optional logger; defaults to ``nd.NDPolicyModule``.
        """
        self.log = logger or logging.getLogger("nd.NDPolicyModule")
        self.nd = nd
        self.module = nd.module
        self.results = results

        # Module parameters
        self.fabric_name = self.module.params.get("fabric_name")
        self.config = self.module.params.get("config")
        self.state = self.module.params.get("state")
        self.use_desc_as_key = self.module.params.get("use_desc_as_key")
        self.create_additional_policy = self.module.params.get("create_additional_policy")
        self.deploy = self.module.params.get("deploy")
        self.ticket_id = self.module.params.get("ticket_id")
        self.cluster_name = self.module.params.get("cluster_name")
        self.check_mode = self.module.check_mode

        # Template parameter cache: {templateName: [param_dict, ...]}
        # Populated lazily by _fetch_template_params() to avoid
        # redundant API calls when multiple config entries share the
        # same template.
        self._template_params_cache: Dict[str, List[Dict]] = {}

        self.log.info(
            f"Initialized NDPolicyModule for fabric: {self.fabric_name}, state: {self.state}"
        )

    def exit_json(self) -> None:
        """Build final result from all registered tasks and exit.

        Merges the ``Results`` aggregation and delegates to
        ``ansible_module.exit_json`` or ``fail_json``.
        """
        self.results.build_final_result()
        final = self.results.final_result

        if True in self.results.failed:
            self.module.fail_json(
                msg="Policy operation failed. See task results for details.",
                **final,
            )
        self.module.exit_json(**final)

    # =========================================================================
    # Public API – State Management
    # =========================================================================

    def manage_state(self) -> None:
        """Main entry point for state management.

        Reads ``self.state`` and delegates to the appropriate handler:
            - **merged**  – create / update / skip policies
            - **query**   – read-only lookup
            - **deleted** – markDelete → pushConfig → remove
        """
        self.log.info(f"Managing state: {self.state}")

        if self.state == "merged":
            self._handle_merged_state()
        elif self.state == "query":
            self._handle_query_state()
        elif self.state == "deleted":
            self._handle_deleted_state()
        else:
            self.module.fail_json(msg=f"Unsupported state: {self.state}")

    # =========================================================================
    # State Handlers
    # =========================================================================

    def _handle_merged_state(self) -> None:
        """Handle state=merged: create, update, or skip policies."""
        self.log.debug("ENTER: _handle_merged_state()")
        self.log.info("Handling merged state")
        self.log.debug(f"Config entries: {len(self.config)}")

        # Phase 1: Build want and have for each config entry
        diff_results = []
        for config_entry in self.config:
            want = self._build_want(config_entry, state="merged")

            # Phase 1a: Validate templateInputs against template schema
            template_name = want.get("templateName")
            template_inputs = want.get("templateInputs") or {}
            if template_name and not self._is_policy_id(template_name):
                validation_errors = self._validate_template_inputs(
                    template_name, template_inputs
                )
                if validation_errors:
                    error_msg = (
                        f"Template input validation failed for '{template_name}': "
                        + "; ".join(validation_errors)
                    )
                    self.log.error(error_msg)
                    diff_results.append({
                        "action": "fail",
                        "want": want,
                        "have": None,
                        "diff": None,
                        "policy_id": None,
                        "error_msg": error_msg,
                    })
                    continue

            have_list, error_msg = self._build_have(want)

            if error_msg:
                self.log.error(f"Build have failed: {error_msg}")
                diff_results.append({
                    "action": "fail",
                    "want": want,
                    "have": None,
                    "diff": None,
                    "policy_id": None,
                    "error_msg": error_msg,
                })
                continue

            # Phase 2: Compute diff
            diff_entry = self._get_diff_merged_single(want, have_list)
            self.log.debug(
                f"Diff result for {want.get('templateName', want.get('policyId', 'unknown'))}: "
                f"action={diff_entry['action']}"
            )
            diff_results.append(diff_entry)

        self.log.info(f"Computed {len(diff_results)} diff results")

        # Phase 3: Execute actions
        policy_ids_to_deploy = self._execute_merged(diff_results)

        # Phase 4: Deploy if requested
        if self.deploy and policy_ids_to_deploy:
            self.log.info(f"Deploying {len(policy_ids_to_deploy)} policies")
            self._deploy_policies(policy_ids_to_deploy)
        elif not self.deploy:
            self.log.info("Deploy not requested, skipping pushConfig")

        self.log.debug("EXIT: _handle_merged_state()")

    def _handle_query_state(self) -> None:
        """Handle state=query: read-only lookup of policies."""
        self.log.debug("ENTER: _handle_query_state()")
        self.log.info("Handling query state")
        self.log.debug(f"Config entries: {len(self.config)}")

        # Phase 1: Build want and have for each config entry
        diff_results = []
        for config_entry in self.config:
            want = self._build_want(config_entry, state="query")
            have_list, error_msg = self._build_have(want)

            if error_msg:
                self.log.error(f"Build have failed: {error_msg}")
                diff_results.append({
                    "action": "fail",
                    "want": want,
                    "policies": [],
                    "match_count": 0,
                    "warning": None,
                    "error_msg": error_msg,
                })
                continue

            self.log.debug(
                f"Found {len(have_list)} existing policies for "
                f"{want.get('templateName', want.get('policyId', 'switch-only'))}"
            )

            # Phase 2: Compute query result
            diff_entry = self._get_diff_query_single(want, have_list)
            diff_results.append(diff_entry)

        # Phase 3: Register results
        self.log.info(f"Computed {len(diff_results)} query results")
        self._execute_query(diff_results)
        self.log.debug("EXIT: _handle_query_state()")

    def _handle_deleted_state(self) -> None:
        """Handle state=deleted: remove policies from NDFC."""
        self.log.debug("ENTER: _handle_deleted_state()")
        self.log.info("Handling deleted state")
        self.log.debug(f"Config entries: {len(self.config)}")

        # Phase 1: Build want and have for each config entry
        diff_results = []
        for config_entry in self.config:
            want = self._build_want(config_entry, state="deleted")
            have_list, error_msg = self._build_have(want)

            if error_msg:
                self.log.error(f"Build have failed: {error_msg}")
                diff_results.append({
                    "action": "fail",
                    "want": want,
                    "policies": [],
                    "policy_ids": [],
                    "match_count": 0,
                    "warning": None,
                    "error_msg": error_msg,
                })
                continue

            # Phase 2: Compute delete result
            diff_entry = self._get_diff_deleted_single(want, have_list)
            self.log.debug(
                f"Delete diff for {want.get('templateName', want.get('policyId', 'switch-only'))}: "
                f"action={diff_entry['action']}"
            )
            diff_results.append(diff_entry)

        # Phase 3: Execute delete actions
        self.log.info(f"Computed {len(diff_results)} delete results")
        self._execute_deleted(diff_results)
        self.log.debug("EXIT: _handle_deleted_state()")

    # =========================================================================
    # Helpers: Classification & Filtering
    # =========================================================================

    @staticmethod
    def _is_policy_id(name: str) -> bool:
        """Return True if name looks like a policy ID (starts with POLICY-)."""
        return name.upper().startswith("POLICY-")

    @staticmethod
    def _build_lucene_filter(**kwargs: Any) -> str:
        """Build a Lucene filter string from keyword arguments.

        Example::

            _build_lucene_filter(switchId="FDO123", templateName="feature_enable")
            # Returns: "switchId:FDO123 AND templateName:feature_enable"
        """
        parts = []
        for key, value in kwargs.items():
            if value is not None:
                parts.append(f"{key}:{value}")
        return " AND ".join(parts)

    @staticmethod
    def _policies_differ(want: Dict, have: Dict) -> Dict:
        """Compare want vs have policy to determine if an update is needed.

        Fields compared:
            - description
            - priority
            - templateInputs (only keys the user specified, with str() normalization.
              The controller injects extra keys like FABRIC_NAME that we must ignore.)

        Fields NOT compared (identity/read-only):
            - policyId, switchId, templateName, source
            - entityType, entityName, createTimestamp, updateTimestamp
            - generatedConfig, markDeleted

        Returns:
            Dict with changed fields, or empty dict if identical.
        """
        diff = {}

        # Compare description
        want_desc = want.get("description", "") or ""
        have_desc = have.get("description", "") or ""
        if want_desc != have_desc:
            diff["description"] = {"want": want_desc, "have": have_desc}

        # Compare priority
        want_priority = want.get("priority", 500)
        have_priority = have.get("priority", 500)
        if want_priority != have_priority:
            diff["priority"] = {"want": want_priority, "have": have_priority}

        # Compare templateInputs — only check keys the user specified.
        # The controller injects additional keys (e.g., FABRIC_NAME) that
        # the user didn't provide. We must ignore those to avoid false diffs.
        want_inputs = want.get("templateInputs") or {}
        have_inputs = have.get("templateInputs") or {}
        input_diff = {}
        for key in want_inputs:
            want_val = str(want_inputs[key])
            have_val = str(have_inputs.get(key, ""))
            if want_val != have_val:
                input_diff[key] = {"want": want_inputs[key], "have": have_inputs.get(key)}
        if input_diff:
            diff["templateInputs"] = input_diff

        return diff

    # =========================================================================
    # API Query Helpers
    # =========================================================================

    def _query_policies(self, lucene_filter: Optional[str] = None) -> List[Dict]:
        """Query policies from the controller using GET /policies.

        Args:
            lucene_filter: Optional Lucene filter string.

        Returns:
            List of policy dicts from the response.
        """
        self.log.debug(f"Querying policies with filter: {lucene_filter}")

        ep = EpApiV1ManagePoliciesGet()
        ep.fabric_name = self.fabric_name
        if self.cluster_name:
            ep.endpoint_params.cluster_name = self.cluster_name
        if lucene_filter:
            ep.lucene_params.filter = lucene_filter
        # Set max to retrieve all matching policies.
        # Default page size is 10 which causes missed matches.
        ep.lucene_params.max = 10000

        data = self.nd.request(ep.path, ep.verb)
        # Response format: {"policies": [...], "meta": {"counts": {"total": N, "remaining": N}}}
        if isinstance(data, dict):
            policies = data.get("policies", [])
            self.log.debug(f"Raw query returned {len(policies)} policies")
            # Filter out:
            # 1. Policies marked for deletion (markDeleted=True) — they have negated
            #    priority and are pending removal. Should not match for idempotency.
            # 2. Shadow/pending sub-policies (source != "") — when a policy is modified
            #    but not yet deployed, NDFC creates a shadow copy with the original
            #    policyId in the 'source' field. Including these causes false matches.
            filtered = [
                p for p in policies
                if not p.get("markDeleted", False)
                and p.get("source", "") == ""
            ]
            self.log.debug(
                f"After filtering markDeleted/source: {len(filtered)} policies "
                f"(removed {len(policies) - len(filtered)})"
            )
            return filtered
        self.log.debug("Query returned non-dict response, returning empty list")
        return []

    def _query_policy_by_id(self, policy_id: str) -> Optional[Dict]:
        """Query a single policy by its ID.

        Args:
            policy_id: Policy ID (e.g., "POLICY-121110").

        Returns:
            Policy dict, or None if not found.
        """
        self.log.debug(f"Looking up policy by ID: {policy_id}")

        ep = EpApiV1ManagePoliciesGet()
        ep.fabric_name = self.fabric_name
        ep.policy_id = policy_id
        if self.cluster_name:
            ep.endpoint_params.cluster_name = self.cluster_name

        try:
            data = self.nd.request(ep.path, ep.verb)
            if isinstance(data, dict) and data:
                self.log.debug(f"Policy {policy_id} found")
                return data
            self.log.info(f"Policy {policy_id} not found (empty response)")
            return None
        except NDModuleError as error:
            # 404 means policy not found
            if error.status == 404:
                self.log.info(f"Policy {policy_id} not found (404)")
                return None
            raise

    # =========================================================================
    # Core: Build want / have
    # =========================================================================

    def _build_want(self, config_entry: Dict, state: str = "merged") -> Dict:
        """Translate a single user config entry to the API-compatible want dict.

        For merged state, ``name`` is required and all fields are included.
        For query/deleted state, ``name`` is optional — when omitted, only
        ``switchId`` is set, which means "return all policies on this switch".

        Args:
            config_entry: Single dict from the user's config list.
            state: Module state ("merged", "query", or "deleted").

        Returns:
            Dict with camelCase keys matching the API schema.
        """
        self.log.debug(f"Building want for state={state}, name={config_entry.get('name')}")

        want = {
            "switchId": config_entry["switch"],
        }

        name = config_entry.get("name")

        if name and self._is_policy_id(name):
            want["policyId"] = name
        elif name:
            want["templateName"] = name

        # For merged state, include all payload fields
        if state == "merged":
            want["entityType"] = config_entry.get("entity_type", "switch")
            want["entityName"] = config_entry.get("entity_name", "SWITCH")
            want["description"] = config_entry.get("description", "")
            want["priority"] = config_entry.get("priority", 500)
            want["templateInputs"] = config_entry.get("template_inputs") or {}
        else:
            # For query/deleted state, only include description if provided
            description = config_entry.get("description", "")
            if description:
                want["description"] = description

        self.log.debug(f"Built want: {want}")
        return want

    # =========================================================================
    # Template Input Validation
    # =========================================================================

    def _fetch_template_params(self, template_name: str) -> List[Dict]:
        """Fetch and cache parameter definitions for a config template.

        Calls ``GET /api/v1/manage/configTemplates/{templateName}`` and
        extracts the ``parameters`` array. Results are cached per
        ``template_name`` so multiple config entries sharing the same
        template incur only one API call.

        Args:
            template_name: The NDFC template name (e.g., ``switch_freeform``).

        Returns:
            List of parameter dicts, each with at minimum ``name``,
            ``parameterType``, ``optional``, and ``defaultValue`` keys.
            Returns an empty list if the template has no parameters or
            the API call fails.
        """
        self.log.debug(f"ENTER: _fetch_template_params(template_name={template_name})")

        if template_name in self._template_params_cache:
            self.log.debug(
                f"Template params cache hit for '{template_name}': "
                f"{len(self._template_params_cache[template_name])} params"
            )
            return self._template_params_cache[template_name]

        ep = EpApiV1ManageConfigTemplatesGet()
        ep.template_name = template_name

        try:
            data = self.nd.request(ep.path, ep.verb)
        except Exception as exc:
            self.log.warning(
                f"Failed to fetch template '{template_name}' parameters: {exc}. "
                "Skipping template input validation."
            )
            self._template_params_cache[template_name] = []
            return []

        # The response is a templateData object with 'parameters' key.
        # 'parameters' is a list of templateParameter objects.
        params = data.get("parameters") if isinstance(data, dict) else []
        if params is None:
            params = []

        self._template_params_cache[template_name] = params
        self.log.info(
            f"Fetched {len(params)} parameter definitions for template '{template_name}'"
        )
        self.log.debug(
            f"Template '{template_name}' param names: "
            f"{[p.get('name') for p in params]}"
        )
        self.log.debug(f"EXIT: _fetch_template_params()")
        return params

    def _validate_template_inputs(
        self, template_name: str, template_inputs: Dict[str, Any]
    ) -> List[str]:
        """Validate user-provided templateInputs against the template schema.

        Performs three checks:
            1. **Unknown keys** — every key in ``template_inputs`` must
               correspond to a parameter ``name`` in the template definition.
            2. **Missing required parameters** — every parameter where
               ``optional`` is ``False`` AND ``defaultValue`` is empty/null
               must be supplied by the user.
            3. **Basic type validation** — lightweight format checks for
               common ``parameterType`` values (boolean, Integer, ipV4Address,
               etc.). Values that fail these checks are reported as warnings,
               not hard failures, because the controller's own validation is
               authoritative.

        Args:
            template_name: Template name for fetching parameter definitions.
            template_inputs: User-provided ``templateInputs`` dict.

        Returns:
            List of validation error message strings. Empty list means all
            inputs are valid.
        """
        self.log.debug(
            f"ENTER: _validate_template_inputs(template={template_name}, "
            f"input_keys={list(template_inputs.keys())})"
        )

        params = self._fetch_template_params(template_name)
        if not params:
            self.log.debug("No template params available, skipping validation")
            return []

        errors: List[str] = []

        # Build lookup: param_name -> param_def
        param_map: Dict[str, Dict] = {}
        for p in params:
            name = p.get("name")
            if name:
                param_map[name] = p

        # ------------------------------------------------------------------
        # Check 1: Unknown keys
        # ------------------------------------------------------------------
        valid_names = set(param_map.keys())
        for user_key in template_inputs:
            if user_key not in valid_names:
                errors.append(
                    f"Unknown templateInput key '{user_key}' for template "
                    f"'{template_name}'. Valid keys: {sorted(valid_names)}"
                )

        # ------------------------------------------------------------------
        # Check 2: Missing required parameters
        # ------------------------------------------------------------------
        for pname, pdef in param_map.items():
            is_optional = pdef.get("optional", True)
            default_val = pdef.get("defaultValue")
            has_default = default_val is not None and str(default_val).strip() != ""

            if not is_optional and not has_default and pname not in template_inputs:
                errors.append(
                    f"Required templateInput '{pname}' (type={pdef.get('parameterType', '?')}) "
                    f"is missing for template '{template_name}'"
                )

        # ------------------------------------------------------------------
        # Check 3: Basic type validation (soft checks)
        # ------------------------------------------------------------------
        for user_key, user_val in template_inputs.items():
            pdef = param_map.get(user_key)
            if not pdef:
                continue  # Already flagged as unknown above

            ptype = (pdef.get("parameterType") or "").lower()
            val_str = str(user_val)

            if ptype == "boolean":
                if val_str.lower() not in ("true", "false"):
                    errors.append(
                        f"templateInput '{user_key}' for template '{template_name}' "
                        f"expects boolean (true/false), got '{val_str}'"
                    )

            elif ptype == "integer":
                try:
                    int(val_str)
                except ValueError:
                    errors.append(
                        f"templateInput '{user_key}' for template '{template_name}' "
                        f"expects integer, got '{val_str}'"
                    )

            elif ptype == "long":
                try:
                    int(val_str)
                except ValueError:
                    errors.append(
                        f"templateInput '{user_key}' for template '{template_name}' "
                        f"expects long integer, got '{val_str}'"
                    )

            elif ptype == "float":
                try:
                    float(val_str)
                except ValueError:
                    errors.append(
                        f"templateInput '{user_key}' for template '{template_name}' "
                        f"expects float, got '{val_str}'"
                    )

            elif ptype in ("ipv4address", "ipaddress"):
                # Basic IPv4 check
                ipv4_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
                if not re.match(ipv4_pattern, val_str):
                    errors.append(
                        f"templateInput '{user_key}' for template '{template_name}' "
                        f"expects IPv4 address (e.g., 192.168.1.1), got '{val_str}'"
                    )

            elif ptype == "ipv4addresswithsubnet":
                ipv4_subnet_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$"
                if not re.match(ipv4_subnet_pattern, val_str):
                    errors.append(
                        f"templateInput '{user_key}' for template '{template_name}' "
                        f"expects IPv4 address with subnet (e.g., 192.168.1.1/24), got '{val_str}'"
                    )

            elif ptype == "macaddress":
                mac_pattern = r"^([0-9a-fA-F]{4}\.){2}[0-9a-fA-F]{4}$|^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$"
                if not re.match(mac_pattern, val_str):
                    errors.append(
                        f"templateInput '{user_key}' for template '{template_name}' "
                        f"expects MAC address, got '{val_str}'"
                    )

            elif ptype == "enum":
                # If metaProperties contains 'validValues', check against them
                meta = pdef.get("metaProperties") or {}
                valid_values_str = meta.get("validValues")
                if valid_values_str:
                    # validValues format is typically "val1,val2,val3"
                    valid_values = [v.strip() for v in valid_values_str.split(",")]
                    if val_str not in valid_values:
                        errors.append(
                            f"templateInput '{user_key}' for template '{template_name}' "
                            f"expects one of {valid_values}, got '{val_str}'"
                        )

        if errors:
            self.log.warning(
                f"Template input validation found {len(errors)} errors "
                f"for template '{template_name}': {errors}"
            )
        else:
            self.log.debug(
                f"Template input validation passed for template '{template_name}'"
            )

        self.log.debug("EXIT: _validate_template_inputs()")
        return errors

    def _build_have(self, want: Dict) -> Tuple[List[Dict], Optional[str]]:
        """Query the controller to find existing policies matching the want.

        Handles all lookup strategies:
            - Case A: Policy ID given → direct lookup
            - Case B: use_desc_as_key=false, templateName given → switchId + templateName
            - Case C: use_desc_as_key=true, templateName given → switchId + description
            - Case D: Switch-only (no templateName or policyId) → all policies on switch

        Returns:
            Tuple of (have_list, error_msg).
        """
        self.log.debug("ENTER: _build_have()")

        # Case A: Policy ID given directly
        if "policyId" in want:
            self.log.debug(f"Case A: Direct policy ID lookup: {want['policyId']}")
            policy = self._query_policy_by_id(want["policyId"])
            if policy:
                self.log.info(f"Policy {want['policyId']} found")
                return [policy], None
            self.log.info(f"Policy {want['policyId']} not found")
            return [], None

        # Case D: Switch-only — no name or policyId given
        if "templateName" not in want:
            self.log.debug(f"Case D: Switch-only lookup for {want['switchId']}")
            lucene = self._build_lucene_filter(switchId=want["switchId"])
            policies = self._query_policies(lucene)
            self.log.info(f"Found {len(policies)} policies on switch {want['switchId']}")
            return policies, None

        # Case B: use_desc_as_key=false, search by switchId + templateName
        if not self.use_desc_as_key:
            self.log.debug(
                f"Case B: Lookup by switchId={want['switchId']} + "
                f"templateName={want['templateName']}"
            )
            lucene = self._build_lucene_filter(
                switchId=want["switchId"],
                templateName=want["templateName"],
            )
            policies = self._query_policies(lucene)

            # If description is provided, use it as an additional post-filter
            want_desc = want.get("description", "")
            if want_desc:
                pre_filter_count = len(policies)
                policies = [
                    p for p in policies
                    if (p.get("description", "") or "") == want_desc
                ]
                self.log.debug(
                    f"Post-filtered by description: {len(policies)} of {pre_filter_count}"
                )

            self.log.info(f"Case B matched {len(policies)} policies")
            return policies, None

        # Case C: use_desc_as_key=true, search by switchId + description
        self.log.debug(
            f"Case C: Lookup by switchId={want['switchId']} + "
            f"description='{want_desc}'"
        )
        want_desc = want.get("description", "") or ""
        if not want_desc:
            self.log.warning("Case C: description is required but not provided")
            return [], "description is required when use_desc_as_key=true and name is a template name"

        lucene = self._build_lucene_filter(
            switchId=want["switchId"],
            description=want_desc,
        )
        policies = self._query_policies(lucene)

        # IMPORTANT: Lucene does tokenized matching, not exact match.
        # Post-filter to ensure exact description match.
        exact_matches = [
            p for p in policies
            if (p.get("description", "") or "") == want_desc
        ]
        self.log.debug(
            f"Exact description match: {len(exact_matches)} of {len(policies)}"
        )

        # For query state with use_desc_as_key=true, also filter by templateName
        # so the user can narrow results to a specific template.
        template_name = want.get("templateName")
        if template_name:
            pre_count = len(exact_matches)
            exact_matches = [
                p for p in exact_matches
                if p.get("templateName") == template_name
            ]
            self.log.debug(
                f"Post-filtered by templateName={template_name}: "
                f"{len(exact_matches)} of {pre_count}"
            )

        self.log.info(f"Case C matched {len(exact_matches)} policies")
        self.log.debug("EXIT: _build_have()")
        return exact_matches, None

    # =========================================================================
    # Diff: Merged State (16 cases)
    # =========================================================================

    def _get_diff_merged_single(self, want: Dict, have_list: List[Dict]) -> Dict:
        """Compute the diff and determine the action for a single config entry.

        Returns:
            Dict with keys: action, want, have, diff, policy_id, error_msg.
        """
        result = {
            "action": None,
            "want": want,
            "have": None,
            "diff": None,
            "policy_id": None,
            "error_msg": None,
        }

        match_count = len(have_list)

        # =================================================================
        # CASES 1-6: Template name given, use_desc_as_key=false
        # =================================================================
        if not self.use_desc_as_key and "templateName" in want:
            if match_count == 0:
                # Case 1: No match → CREATE
                result["action"] = "create"
                return result

            if match_count == 1:
                have = have_list[0]
                diff = self._policies_differ(want, have)
                result["have"] = have
                result["policy_id"] = have.get("policyId")

                if not diff:
                    # Case 2: Match, no diff → SKIP
                    result["action"] = "skip"
                    return result

                if self.create_additional_policy:
                    # Case 3: Match, has diff, create_additional=true → CREATE duplicate
                    result["action"] = "create"
                    result["diff"] = diff
                    return result

                # Case 4: Match, has diff, create_additional=false → UPDATE
                result["action"] = "update"
                result["diff"] = diff
                return result

            # match_count >= 2
            if self.create_additional_policy:
                # Case 5: Multiple matches, create_additional=true → CREATE another
                result["action"] = "create"
                return result

            # Case 6: Multiple matches, create_additional=false → SKIP
            result["action"] = "skip"
            return result

        # =================================================================
        # CASES 7-11: Policy ID given
        # =================================================================
        if "policyId" in want:
            if match_count == 0:
                # Case 7: Policy ID not found → SKIP
                result["action"] = "skip"
                result["error_msg"] = (
                    f"Policy {want['policyId']} not found. "
                    "Cannot create a policy with a specific ID."
                )
                return result

            have = have_list[0]
            diff = self._policies_differ(want, have)
            result["have"] = have
            result["policy_id"] = have.get("policyId")

            # Carry forward templateName from existing policy for update payload
            if "templateName" not in want and "templateName" in have:
                want["templateName"] = have["templateName"]

            if not diff:
                # Case 8: Match, no diff → SKIP
                result["action"] = "skip"
                return result

            if self.create_additional_policy:
                # Case 9: Match, has diff, create_additional=true → CREATE duplicate
                result["action"] = "create"
                result["diff"] = diff
                return result

            # Case 10/11: Match, has diff, create_additional=false → UPDATE
            result["action"] = "update"
            result["diff"] = diff
            return result

        # =================================================================
        # CASES 12-16: use_desc_as_key=true
        # =================================================================
        if self.use_desc_as_key:
            if match_count == 0:
                # Case 12: No match → CREATE
                result["action"] = "create"
                return result

            if match_count == 1:
                have = have_list[0]
                result["have"] = have
                result["policy_id"] = have.get("policyId")

                # Check if template matches
                templates_match = want.get("templateName") == have.get("templateName")

                if templates_match:
                    diff = self._policies_differ(want, have)
                    if not diff:
                        # Case 13: Same template, no diff → SKIP
                        result["action"] = "skip"
                        return result

                    # Case 14: Same template, fields differ → UPDATE
                    result["action"] = "update"
                    result["diff"] = diff
                    return result

                # Case 15: Different template → DELETE old + CREATE new
                result["action"] = "delete_and_create"
                result["diff"] = {
                    "templateName": {
                        "want": want.get("templateName"),
                        "have": have.get("templateName"),
                    }
                }
                return result

            # Case 16: Multiple matches → FAIL (ambiguous)
            result["action"] = "fail"
            result["error_msg"] = (
                f"Multiple policies ({match_count}) found with description "
                f"'{want.get('description')}' on switch {want.get('switchId')}. "
                "Cannot determine which policy to update. "
                "Use a policy ID directly or ensure descriptions are unique."
            )
            return result

        # Should not reach here
        result["action"] = "fail"
        result["error_msg"] = "Unable to determine action for policy config."
        return result

    # =========================================================================
    # Execute: Merged State
    # =========================================================================

    def _execute_merged(self, diff_results: List[Dict]) -> List[str]:
        """Execute the computed actions for all config entries.

        Args:
            diff_results: List of diff result dicts from _get_diff_merged_single.

        Returns:
            List of policy IDs to deploy (if deploy=true).
        """
        self.log.debug("ENTER: _execute_merged()")
        self.log.debug(f"Processing {len(diff_results)} diff entries")
        policy_ids_to_deploy = []

        for diff_entry in diff_results:
            action = diff_entry["action"]
            want = diff_entry["want"]
            have = diff_entry["have"]
            policy_id = diff_entry["policy_id"]
            field_diff = diff_entry["diff"]
            error_msg = diff_entry["error_msg"]

            self.log.info(
                f"Executing action={action} for "
                f"{want.get('templateName', want.get('policyId', 'unknown'))}"
            )

            # --- FAIL ---
            if action == "fail":
                self._register_result(
                    action="policy_merged",
                    operation_type=OperationType.UPDATE,
                    return_code=-1,
                    message=error_msg,
                    success=False,
                    found=False,
                    diff={"action": action, "want": want, "error": error_msg},
                )
                continue

            # --- SKIP ---
            if action == "skip":
                diff_payload = {"action": action, "want": want}
                if error_msg:
                    diff_payload["warning"] = error_msg
                self._register_result(
                    action="policy_merged",
                    operation_type=OperationType.QUERY,
                    return_code=200,
                    message="No changes needed",
                    data=have or {},
                    success=True,
                    found=have is not None,
                    diff=diff_payload,
                )
                continue

            # --- CREATE ---
            if action == "create":
                if self.check_mode:
                    self._register_result(
                        action="policy_create",
                        operation_type=OperationType.CREATE,
                        return_code=200,
                        message="OK (check_mode)",
                        success=True,
                        found=False,
                        diff={"action": action, "want": want, "diff": field_diff},
                    )
                    continue

                created_id = self._api_create_policy(want)
                if created_id:
                    policy_ids_to_deploy.append(created_id)

                self.results.response_current = self.nd.rest_send.response_current
                self.results.result_current = self.nd.rest_send.result_current
                self.results.diff_current = {
                    "action": action,
                    "want": want,
                    "diff": field_diff,
                    "created_policy_id": created_id,
                }
                self.results.action = "policy_create"
                self.results.state = "merged"
                self.results.check_mode = self.check_mode
                self.results.operation_type = OperationType.CREATE
                self.results.register_task_result()
                continue

            # --- UPDATE ---
            if action == "update":
                if self.check_mode:
                    self._register_result(
                        action="policy_update",
                        operation_type=OperationType.UPDATE,
                        return_code=200,
                        message="OK (check_mode)",
                        success=True,
                        found=True,
                        diff={
                            "action": action,
                            "want": want,
                            "have": have,
                            "diff": field_diff,
                            "policy_id": policy_id,
                        },
                    )
                    continue

                self._api_update_policy(want, have, policy_id)
                policy_ids_to_deploy.append(policy_id)

                self.results.response_current = self.nd.rest_send.response_current
                self.results.result_current = self.nd.rest_send.result_current
                self.results.diff_current = {
                    "action": action,
                    "want": want,
                    "have": have,
                    "diff": field_diff,
                    "policy_id": policy_id,
                }
                self.results.action = "policy_update"
                self.results.state = "merged"
                self.results.check_mode = self.check_mode
                self.results.operation_type = OperationType.UPDATE
                self.results.register_task_result()
                continue

            # --- DELETE_AND_CREATE ---
            if action == "delete_and_create":
                if self.check_mode:
                    self._register_result(
                        action="policy_replace",
                        operation_type=OperationType.UPDATE,
                        return_code=200,
                        message="OK (check_mode)",
                        success=True,
                        found=True,
                        diff={
                            "action": action,
                            "want": want,
                            "have": have,
                            "diff": field_diff,
                            "delete_policy_id": policy_id,
                        },
                    )
                    continue

                # Step 1: Delete the old policy
                self._api_remove_policies([policy_id])

                # Step 2: Create the new policy
                created_id = self._api_create_policy(want)
                if created_id:
                    policy_ids_to_deploy.append(created_id)

                self.results.response_current = self.nd.rest_send.response_current
                self.results.result_current = self.nd.rest_send.result_current
                self.results.diff_current = {
                    "action": action,
                    "want": want,
                    "have": have,
                    "diff": field_diff,
                    "deleted_policy_id": policy_id,
                    "created_policy_id": created_id,
                }
                self.results.action = "policy_replace"
                self.results.state = "merged"
                self.results.check_mode = self.check_mode
                self.results.operation_type = OperationType.UPDATE
                self.results.register_task_result()
                continue

        self.log.info(f"Merged execute complete: {len(policy_ids_to_deploy)} policies to deploy")
        self.log.debug("EXIT: _execute_merged()")
        return policy_ids_to_deploy

    # =========================================================================
    # Diff: Query State (13 cases)
    # =========================================================================

    def _get_diff_query_single(self, want: Dict, have_list: List[Dict]) -> Dict:
        """Compute the query result for a single config entry.

        Returns:
            Dict with keys: action, want, policies, match_count, warning, error_msg.
        """
        result = {
            "action": None,
            "want": want,
            "policies": have_list,
            "match_count": len(have_list),
            "warning": None,
            "error_msg": None,
        }

        match_count = len(have_list)

        # Q-1, Q-2: Policy ID given
        if "policyId" in want:
            result["action"] = "found" if match_count >= 1 else "not_found"
            return result

        # Switch-only: No name given → return everything found on this switch
        if "templateName" not in want:
            result["action"] = "found" if match_count >= 1 else "not_found"
            return result

        # Q-3 to Q-9: Template name given, use_desc_as_key=false
        if not self.use_desc_as_key:
            result["action"] = "found" if match_count > 0 else "not_found"
            return result

        # Q-10 to Q-13: Template name given, use_desc_as_key=true
        if self.use_desc_as_key:
            want_desc = want.get("description", "")
            if not want_desc:
                # Q-10: description required but not given
                result["action"] = "fail"
                result["error_msg"] = (
                    "description is required when use_desc_as_key=true "
                    "and name is a template name."
                )
                return result

            if match_count == 0:
                result["action"] = "not_found"
                return result

            if match_count == 1:
                result["action"] = "found"
                return result

            # Q-13: Multiple matches → return all with warning
            result["action"] = "found"
            result["warning"] = (
                f"Multiple policies ({match_count}) found with description "
                f"'{want_desc}' and template '{want.get('templateName')}' on "
                f"switch {want.get('switchId')}. Descriptions are not unique."
            )
            return result

        # Should not reach here
        result["action"] = "not_found"
        return result

    # =========================================================================
    # Execute: Query State
    # =========================================================================

    def _execute_query(self, diff_results: List[Dict]) -> None:
        """Register results for all query config entries.

        Query state never makes changes — ``changed`` is always ``false``.
        """
        self.log.debug("ENTER: _execute_query()")
        self.log.debug(f"Processing {len(diff_results)} query entries")

        for diff_entry in diff_results:
            action = diff_entry["action"]
            want = diff_entry["want"]
            policies = diff_entry["policies"]
            match_count = diff_entry["match_count"]
            warning = diff_entry["warning"]
            error_msg = diff_entry["error_msg"]

            self.log.debug(
                f"Query action={action} for "
                f"{want.get('templateName', want.get('policyId', 'switch-only'))}, "
                f"match_count={match_count}"
            )

            if action == "fail":
                self.log.warning(f"Query failed: {error_msg}")
                self._register_result(
                    action="policy_query",
                    state="query",
                    operation_type=OperationType.QUERY,
                    return_code=-1,
                    message=error_msg,
                    success=False,
                    found=False,
                    diff={"action": action, "want": want, "error": error_msg},
                )
                continue

            if action == "not_found":
                self._register_result(
                    action="policy_query",
                    state="query",
                    operation_type=OperationType.QUERY,
                    return_code=200,
                    message="Not found",
                    success=True,
                    found=False,
                    diff={"action": action, "want": want, "policies": [], "match_count": 0},
                )
                continue

            if action == "found":
                diff_payload = {
                    "action": action,
                    "want": want,
                    "policies": policies,
                    "match_count": match_count,
                }
                if warning:
                    diff_payload["warning"] = warning
                self._register_result(
                    action="policy_query",
                    state="query",
                    operation_type=OperationType.QUERY,
                    return_code=200,
                    message="OK",
                    data=policies,
                    success=True,
                    found=True,
                    diff=diff_payload,
                )
                continue

        self.log.debug("EXIT: _execute_query()")

    # =========================================================================
    # Diff: Deleted State (16 cases)
    # =========================================================================

    def _get_diff_deleted_single(self, want: Dict, have_list: List[Dict]) -> Dict:
        """Compute the delete result for a single config entry.

        Returns:
            Dict with keys: action, want, policies, policy_ids, match_count,
            warning, error_msg.
        """
        policy_ids = [p.get("policyId") for p in have_list if p.get("policyId")]
        result = {
            "action": None,
            "want": want,
            "policies": have_list,
            "policy_ids": policy_ids,
            "match_count": len(have_list),
            "warning": None,
            "error_msg": None,
        }

        match_count = len(have_list)

        # D-7, D-8: Policy ID given
        if "policyId" in want:
            if match_count == 0:
                result["action"] = "skip"
            else:
                result["action"] = "delete"
            return result

        # D-13 to D-16: Switch-only (no name given)
        if "templateName" not in want:
            if match_count == 0:
                result["action"] = "skip"
            else:
                result["action"] = "delete_all"
            return result

        # D-1 to D-6: Template name given, use_desc_as_key=false
        if not self.use_desc_as_key:
            if match_count == 0:
                result["action"] = "skip"
            elif match_count == 1:
                result["action"] = "delete"
            else:
                result["action"] = "delete_all"
            return result

        # D-9 to D-12: Template name given, use_desc_as_key=true
        if self.use_desc_as_key:
            want_desc = want.get("description", "")
            if not want_desc:
                # D-9: description required but not given
                result["action"] = "fail"
                result["error_msg"] = (
                    "description is required when use_desc_as_key=true "
                    "and name is a template name."
                )
                return result

            if match_count == 0:
                result["action"] = "skip"
                return result

            if match_count == 1:
                result["action"] = "delete"
                return result

            # D-12: Multiple matches → delete all with warning
            result["action"] = "delete_all"
            result["warning"] = (
                f"Multiple policies ({match_count}) found with description "
                f"'{want_desc}' and template '{want.get('templateName')}' on "
                f"switch {want.get('switchId')}. All will be deleted."
            )
            return result

        # Should not reach here
        result["action"] = "skip"
        return result

    # =========================================================================
    # Execute: Deleted State
    # =========================================================================

    def _execute_deleted(self, diff_results: List[Dict]) -> None:
        """Execute the computed actions for all deleted config entries.

        Collects all policy IDs to delete across all config entries, then
        performs bulk API calls:
            - deploy=true:  markDelete → pushConfig → remove  (3-step)
            - deploy=false: remove only                       (1-step)
        """
        self.log.debug("ENTER: _execute_deleted()")
        self.log.debug(f"Processing {len(diff_results)} delete entries")

        # Phase A: Register per-entry results and collect all policy IDs
        all_policy_ids_to_delete = []

        for diff_entry in diff_results:
            action = diff_entry["action"]
            want = diff_entry["want"]
            policies = diff_entry["policies"]
            policy_ids = diff_entry["policy_ids"]
            match_count = diff_entry["match_count"]
            warning = diff_entry["warning"]
            error_msg = diff_entry["error_msg"]

            self.log.debug(
                f"Delete action={action} for "
                f"{want.get('templateName', want.get('policyId', 'switch-only'))}, "
                f"policy_ids={policy_ids}"
            )

            # --- FAIL ---
            if action == "fail":
                self.log.warning(f"Delete failed: {error_msg}")
                self._register_result(
                    action="policy_deleted",
                    state="deleted",
                    operation_type=OperationType.DELETE,
                    return_code=-1,
                    message=error_msg,
                    success=False,
                    found=False,
                    diff={"action": action, "want": want, "error": error_msg},
                )
                continue

            # --- SKIP ---
            if action == "skip":
                self.log.info(
                    f"Policy not found for deletion: "
                    f"{want.get('templateName', want.get('policyId', 'switch-only'))}"
                )
                self._register_result(
                    action="policy_deleted",
                    state="deleted",
                    operation_type=OperationType.QUERY,
                    return_code=200,
                    message="Policy not found — already absent",
                    success=True,
                    found=False,
                    diff={"action": action, "want": want},
                )
                continue

            # --- DELETE / DELETE_ALL ---
            if action in ("delete", "delete_all"):
                self.log.info(
                    f"Marking {len(policy_ids)} policy(ies) for deletion: {policy_ids}"
                )
                all_policy_ids_to_delete.extend(policy_ids)

                if self.check_mode:
                    self.log.info(f"Check mode: would delete {len(policy_ids)} policy(ies)")
                    diff_payload = {
                        "action": action,
                        "want": want,
                        "policy_ids": policy_ids,
                        "match_count": match_count,
                    }
                    if warning:
                        diff_payload["warning"] = warning
                    self._register_result(
                        action="policy_deleted",
                        state="deleted",
                        operation_type=OperationType.DELETE,
                        return_code=200,
                        message="OK (check_mode)",
                        success=True,
                        found=True,
                        diff=diff_payload,
                    )
                    continue

                # Register intent — actual API calls happen in bulk below
                diff_payload = {
                    "action": action,
                    "want": want,
                    "policy_ids": policy_ids,
                    "match_count": match_count,
                    "policies": policies,
                }
                if warning:
                    diff_payload["warning"] = warning
                self._register_result(
                    action="policy_deleted",
                    state="deleted",
                    operation_type=OperationType.DELETE,
                    return_code=200,
                    message="Pending bulk delete",
                    success=True,
                    found=True,
                    diff=diff_payload,
                )
                continue

        # Phase B: Execute bulk API calls (skip if check_mode or nothing to delete)
        if self.check_mode or not all_policy_ids_to_delete:
            self.log.info(
                "Skipping bulk delete: "
                f"{'check_mode' if self.check_mode else 'no policies to delete'}"
            )
            self.log.debug("EXIT: _execute_deleted()")
            return

        # Deduplicate policy IDs (same policy could match multiple config entries)
        unique_policy_ids = list(dict.fromkeys(all_policy_ids_to_delete))
        self.log.info(
            f"Total policies to delete: {len(unique_policy_ids)} "
            f"(deduplicated from {len(all_policy_ids_to_delete)})"
        )

        # Step 1 (deploy=true only): markDelete — flag policies for deletion
        if self.deploy:
            self.log.info(f"Step 1/3: markDelete for {len(unique_policy_ids)} policies")
            self._api_mark_delete(unique_policy_ids)

            self.results.action = "policy_mark_delete"
            self.results.state = "deleted"
            self.results.check_mode = self.check_mode
            self.results.operation_type = OperationType.DELETE
            self.results.response_current = self.nd.rest_send.response_current
            self.results.result_current = self.nd.rest_send.result_current
            self.results.diff_current = {
                "action": "mark_delete",
                "policy_ids": unique_policy_ids,
            }
            self.results.register_task_result()

        # Step 2 (deploy=true only): pushConfig — push negation config to switches
        if self.deploy:
            self.log.info(f"Step 2/3: pushConfig for {len(unique_policy_ids)} policies")
            self._deploy_policies(unique_policy_ids, state="deleted")

        # Step 3: remove — hard-delete policy records from NDFC
        self.log.info(
            f"{'Step 3/3' if self.deploy else 'Step 1/1'}: "
            f"remove {len(unique_policy_ids)} policies"
        )
        self._api_remove_policies(unique_policy_ids)

        self.results.action = "policy_remove"
        self.results.state = "deleted"
        self.results.check_mode = self.check_mode
        self.results.operation_type = OperationType.DELETE
        self.results.response_current = self.nd.rest_send.response_current
        self.results.result_current = self.nd.rest_send.result_current
        self.results.diff_current = {
            "action": "remove",
            "policy_ids": unique_policy_ids,
        }
        self.results.register_task_result()
        self.log.debug("EXIT: _execute_deleted()")

    # =========================================================================
    # Deploy: pushConfig
    # =========================================================================

    def _deploy_policies(
        self,
        policy_ids: List[str],
        state: str = "merged",
    ) -> None:
        """Deploy policies by calling pushConfig.

        Args:
            policy_ids: List of policy IDs to deploy.
            state: Module state for result reporting.
        """
        if not policy_ids:
            self.log.debug("No policy IDs to deploy, skipping")
            return

        self.log.info(f"Deploying {len(policy_ids)} policies via pushConfig")

        self.results.action = "policy_deploy"
        self.results.state = state
        self.results.check_mode = self.check_mode
        self.results.operation_type = OperationType.UPDATE

        if self.check_mode:
            self.log.info(f"Check mode: would deploy {len(policy_ids)} policies")
            self.results.response_current = {
                "RETURN_CODE": 200,
                "MESSAGE": "OK (check_mode)",
                "DATA": {},
            }
            self.results.result_current = {"success": True, "found": True}
            self.results.diff_current = {
                "action": "deploy",
                "policy_ids": policy_ids,
            }
            self.results.register_task_result()
            return

        push_body = PolicyIds(policy_ids=policy_ids)

        ep = EpApiV1ManagePolicyActionsPushConfig()
        ep.fabric_name = self.fabric_name
        if self.cluster_name:
            ep.endpoint_params.cluster_name = self.cluster_name
        # NOTE: pushConfig does NOT accept ticketId per manage.json spec

        self.nd.request(ep.path, ep.verb, push_body.to_request_dict())

        self.results.response_current = self.nd.rest_send.response_current
        self.results.result_current = self.nd.rest_send.result_current
        self.results.diff_current = {
            "action": "deploy",
            "policy_ids": policy_ids,
        }
        self.results.register_task_result()

    # =========================================================================
    # API Helpers (low-level CRUD)
    # =========================================================================

    def _api_create_policy(self, want: Dict) -> Optional[str]:
        """Create a single policy via POST and return the created policy ID.

        Args:
            want: The want dict with all policy fields.

        Returns:
            Created policy ID string, or None.
        """
        self.log.info(
            f"Creating policy: template={want.get('templateName')}, "
            f"switch={want.get('switchId')}"
        )
        policy_model = PolicyCreate(
            switch_id=want["switchId"],
            template_name=want["templateName"],
            entity_type=want.get("entityType", "switch"),
            entity_name=want.get("entityName", "SWITCH"),
            description=want.get("description", ""),
            priority=want.get("priority", 500),
            source=want.get("source", ""),
            template_inputs=want.get("templateInputs"),
        )
        bulk = PolicyCreateBulk(policies=[policy_model])
        payload = bulk.to_request_dict()

        ep = EpApiV1ManagePoliciesPost()
        ep.fabric_name = self.fabric_name
        if self.cluster_name:
            ep.endpoint_params.cluster_name = self.cluster_name
        if self.ticket_id:
            ep.endpoint_params.ticket_id = self.ticket_id

        data = self.nd.request(ep.path, ep.verb, payload)

        # Parse response to get policy ID
        created_policies = data.get("policies", []) if isinstance(data, dict) else []
        if created_policies:
            created_id = created_policies[0].get("policyId")
            self.log.info(f"Created policy: {created_id}")
            return created_id
        self.log.warning("Create API returned no policy ID")
        return None

    def _api_update_policy(self, want: Dict, have: Dict, policy_id: str) -> None:
        """Update an existing policy via PUT.

        For templateInputs, merge user-specified keys on top of the
        controller's existing values. This matches the old dcnm_policy
        behaviour: start from the controller's nvPairs, then overlay
        only the keys the user provided. This prevents accidentally
        wiping inputs when the user only wants to change description
        or priority.

        Args:
            want: The want dict with desired policy fields.
            have: The existing policy dict from the controller.
            policy_id: The policy ID to update.
        """
        self.log.info(f"Updating policy: {policy_id}")
        merged_inputs = dict(have.get("templateInputs") or {})
        for k, v in (want.get("templateInputs") or {}).items():
            merged_inputs[k] = v
        self.log.debug(f"Merged templateInputs: {len(merged_inputs)} keys")

        update_model = PolicyUpdate(
            switch_id=want["switchId"],
            template_name=want.get("templateName", have.get("templateName")),
            entity_type=want.get("entityType", have.get("entityType", "switch")),
            entity_name=want.get("entityName", have.get("entityName", "SWITCH")),
            description=want.get("description", ""),
            priority=want.get("priority", 500),
            source=want.get("source", have.get("source", "")),
            template_inputs=merged_inputs,
        )
        payload = update_model.to_request_dict()

        ep = EpApiV1ManagePoliciesPut()
        ep.fabric_name = self.fabric_name
        ep.policy_id = policy_id
        if self.cluster_name:
            ep.endpoint_params.cluster_name = self.cluster_name
        if self.ticket_id:
            ep.endpoint_params.ticket_id = self.ticket_id

        self.nd.request(ep.path, ep.verb, payload)

    def _api_mark_delete(self, policy_ids: List[str]) -> None:
        """Mark policies for deletion via POST /policyActions/markDelete.

        Args:
            policy_ids: List of policy IDs to mark-delete.
        """
        self.log.info(f"Marking {len(policy_ids)} policies for deletion: {policy_ids}")
        body = PolicyIds(policy_ids=policy_ids)

        ep = EpApiV1ManagePolicyActionsMarkDelete()
        ep.fabric_name = self.fabric_name
        if self.cluster_name:
            ep.endpoint_params.cluster_name = self.cluster_name
        if self.ticket_id:
            ep.endpoint_params.ticket_id = self.ticket_id

        self.nd.request(ep.path, ep.verb, body.to_request_dict())

    def _api_remove_policies(self, policy_ids: List[str]) -> None:
        """Hard-delete policies via POST /policyActions/remove.

        Args:
            policy_ids: List of policy IDs to remove from NDFC.
        """
        self.log.info(f"Removing {len(policy_ids)} policies: {policy_ids}")
        body = PolicyIds(policy_ids=policy_ids)

        ep = EpApiV1ManagePolicyActionsRemove()
        ep.fabric_name = self.fabric_name
        if self.cluster_name:
            ep.endpoint_params.cluster_name = self.cluster_name
        if self.ticket_id:
            ep.endpoint_params.ticket_id = self.ticket_id

        self.nd.request(ep.path, ep.verb, body.to_request_dict())

    # =========================================================================
    # Results Helper
    # =========================================================================

    def _register_result(
        self,
        action: str,
        operation_type: OperationType,
        return_code: int,
        message: str,
        success: bool,
        found: bool,
        diff: Dict,
        data: Any = None,
        state: Optional[str] = None,
    ) -> None:
        """Register a single task result into the Results aggregator.

        Convenience wrapper to avoid repeating the same boilerplate
        for every action/state combination.

        Args:
            action: Action label (e.g., "policy_create", "policy_query").
            operation_type: OperationType enum value.
            return_code: HTTP return code (or -1 for errors).
            message: Human-readable message.
            success: Whether the operation succeeded.
            found: Whether the policy was found.
            diff: Diff payload dict.
            data: Optional response data.
            state: Override state (defaults to self.state).
        """
        self.results.action = action
        self.results.state = state or self.state
        self.results.check_mode = self.check_mode
        self.results.operation_type = operation_type
        self.results.response_current = {
            "RETURN_CODE": return_code,
            "MESSAGE": message,
            "DATA": data if data is not None else {},
        }
        self.results.result_current = {"success": success, "found": found}
        self.results.diff_current = diff
        self.results.register_task_result()
