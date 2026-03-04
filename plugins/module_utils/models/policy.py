# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pydantic models for Policy API request bodies.

This module provides request body models for all policy-related operations:

- POST /api/v1/manage/fabrics/{fabricName}/policies (create)
- PUT /api/v1/manage/fabrics/{fabricName}/policies/{policyId} (update)
- POST /api/v1/manage/fabrics/{fabricName}/policyActions/markDelete
- POST /api/v1/manage/fabrics/{fabricName}/policyActions/pushConfig
- POST /api/v1/manage/fabrics/{fabricName}/policyActions/remove

## Schemas from manage.json

Based on `createPolicy`, `createBasePolicy`, `policyPut`, and `policyActions` schemas.
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from enum import Enum
from typing import Any, Dict, List, Optional

from ansible_collections.cisco.nd.plugins.module_utils.pydantic_compat import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# ============================================================================
# Enums
# ============================================================================


class PolicyEntityType(str, Enum):
    """
    Valid entity types for policies.

    Based on policyEntityType schema from manage.json.
    """

    SWITCH = "switch"
    CONFIG_PROFILE = "configProfile"
    INTERFACE = "interface"


# ============================================================================
# Policy Create Model
# ============================================================================


class PolicyCreate(BaseModel):
    """
    Request body model for creating a single policy.

    ## Description

    Based on `createPolicy` schema from manage.json which extends `createBasePolicy`.

    ## API Endpoint

    POST /api/v1/manage/fabrics/{fabricName}/policies

    ## Required Fields

    - switch_id: Switch serial number (e.g., "FDO25031SY4")
    - template_name: Name of the policy template (e.g., "switch_freeform", "feature_enable")
    - entity_type: Type of entity (switch, configProfile, interface)
    - entity_name: Name of the entity (e.g., "SWITCH", "Ethernet1/1")

    ## Optional Fields

    - description: Policy description (max 255 chars)
    - priority: Policy priority (1-2000, default 500)
    - source: Source of the policy (e.g., "UNDERLAY", "OVERLAY", "")
    - template_inputs: Name/value pairs passed to the template
    - secondary_entity_name: Secondary entity name (for configProfile)
    - secondary_entity_type: Secondary entity type

    ## Usage

    ```python
    policy = PolicyCreate(
        switch_id="FDO25031SY4",
        template_name="feature_enable",
        entity_type=PolicyEntityType.SWITCH,
        entity_name="SWITCH",
        template_inputs={"featureName": "lacp"},
        priority=500
    )
    payload = policy.to_request_dict()
    ```
    """

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,
    )

    # Required fields from createPolicy schema
    # switchId is required by createPolicy (extends createBasePolicy)
    switch_id: str = Field(
        ...,  # Required field (no default)
        alias="switchId",
        description="Switch serial number (e.g., FDO25031SY4)",
    )
    # templateName is required by createBasePolicy
    template_name: str = Field(
        ...,  # Required field (no default)
        max_length=255,
        alias="templateName",
        description="Name of the policy template",
    )
    # entityType is required by createBasePolicy
    entity_type: PolicyEntityType = Field(
        ...,  # Required field (no default)
        alias="entityType",
        description="Type of the entity (switch, configProfile, interface)",
    )
    # entityName is required by createBasePolicy
    entity_name: str = Field(
        ...,  # Required field (no default)
        max_length=255,
        alias="entityName",
        description="Name of the entity. Use 'SWITCH' for switch-level, or interface name for interface-level",
    )

    # Optional fields
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Description of the policy",
    )
    priority: Optional[int] = Field(
        default=500,
        ge=1,
        le=2000,
        description="Priority of the policy (1-2000)",
    )
    source: Optional[str] = Field(
        default="",
        max_length=255,
        description="Source of the policy (UNDERLAY, OVERLAY, LINK, etc.). Empty means any source can update.",
    )
    template_inputs: Optional[Dict[str, Any]] = Field(
        default=None,
        alias="templateInputs",
        description="Name/value parameter list passed to the template",
    )
    secondary_entity_name: Optional[str] = Field(
        default=None,
        alias="secondaryEntityName",
        description="Name of the secondary entity (e.g., overlay name for configProfile)",
    )
    secondary_entity_type: Optional[PolicyEntityType] = Field(
        default=None,
        alias="secondaryEntityType",
        description="Type of the secondary entity",
    )

    def to_request_dict(self) -> Dict[str, Any]:
        """
        Convert model to API request dictionary with camelCase keys.

        ## Returns

        Dictionary suitable for JSON request body, excluding None values.

        ## Example

        ```python
        policy = PolicyCreate(
            switch_id="FDO123",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH"
        )
        payload = policy.to_request_dict()
        # {"switchId": "FDO123", "templateName": "feature_enable", ...}
        ```
        """
        return self.model_dump(by_alias=True, exclude_none=True)


# ============================================================================
# Policy Create Bulk Model
# ============================================================================


class PolicyCreateBulk(BaseModel):
    """
    Request body model for creating multiple policies in bulk.

    ## Description

    Wrapper for bulk policy creation via POST endpoint.

    ## API Endpoint

    POST /api/v1/manage/fabrics/{fabricName}/policies

    ## Usage

    ```python
    bulk = PolicyCreateBulk(policies=[
        PolicyCreate(
            switch_id="FDO123",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH",
            template_inputs={"featureName": "lacp"}
        ),
        PolicyCreate(
            switch_id="FDO456",
            template_name="power_redundancy",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH",
            template_inputs={"REDUNDANCY_MODE": "ps-redundant"}
        ),
    ])
    payload = bulk.to_request_dict()
    ```
    """

    model_config = ConfigDict(validate_assignment=True)

    policies: List[PolicyCreate] = Field(
        default_factory=list,
        min_length=1,
        description="List of policies to create",
    )

    def to_request_dict(self) -> Dict[str, Any]:
        """
        Convert to API request dictionary.

        ## Returns

        Dictionary with 'policies' key containing list of policy dicts.
        """
        return {"policies": [policy.to_request_dict() for policy in self.policies]}


# ============================================================================
# Policy Update Model
# ============================================================================


class PolicyUpdate(PolicyCreate):
    """
    Request body model for updating a policy.

    ## Description

    Based on `policyPut` schema from manage.json which extends `createPolicy`.
    Inherits all fields from PolicyCreate.

    ## API Endpoint

    PUT /api/v1/manage/fabrics/{fabricName}/policies/{policyId}

    ## Note

    The policyId is passed as a path parameter, not in the request body.
    All fields from PolicyCreate are available for update.

    ## Usage

    ```python
    update = PolicyUpdate(
        switch_id="FDO25031SY4",
        template_name="feature_enable",
        entity_type=PolicyEntityType.SWITCH,
        entity_name="SWITCH",
        template_inputs={"featureName": "lacp"},
        priority=100,  # Updated priority
        description="Updated policy description"
    )
    payload = update.to_request_dict()
    ```
    """

    model_config = ConfigDict(
        validate_assignment=True,
        use_enum_values=True,
        populate_by_name=True,
    )

    # All fields inherited from PolicyCreate
    # policyPut schema is identical to createPolicy per manage.json


# ============================================================================
# Policy Actions Model (markDelete, pushConfig, remove)
# ============================================================================


class PolicyIds(BaseModel):
    """
    Request body model for policy bulk actions.

    ## Description

    Used for markDelete, pushConfig, and remove policy actions.
    Contains a list of policy IDs to perform the action on.

    ## API Endpoints

    - POST /api/v1/manage/fabrics/{fabricName}/policyActions/markDelete
    - POST /api/v1/manage/fabrics/{fabricName}/policyActions/pushConfig
    - POST /api/v1/manage/fabrics/{fabricName}/policyActions/remove

    ## Request Body Schema (from manage.json)

    ```json
    {
      "policyIds": ["POLICY-121110", "POLICY-121120"]
    }
    ```

    ## Usage

    ```python
    # Mark-delete policies
    body = PolicyIds(policy_ids=["POLICY-121110", "POLICY-121120"])
    payload = body.to_request_dict()
    # {"policyIds": ["POLICY-121110", "POLICY-121120"]}

    # Push config for policies
    body = PolicyIds(policy_ids=["POLICY-121110"])
    payload = body.to_request_dict()

    # Remove/delete policies
    body = PolicyIds(policy_ids=["POLICY-121110", "POLICY-121120", "POLICY-121130"])
    payload = body.to_request_dict()
    ```
    """

    model_config = ConfigDict(
        validate_assignment=True,
        populate_by_name=True,
    )

    policy_ids: List[str] = Field(
        default_factory=list,
        min_length=1,
        alias="policyIds",
        description="List of policy IDs to perform action on",
    )

    @field_validator("policy_ids")
    @classmethod
    def validate_policy_ids(cls, v: List[str]) -> List[str]:
        """
        Validate that all policy IDs are non-empty strings.

        ## Parameters

        - v: List of policy IDs

        ## Returns

        - Validated list of policy IDs

        ## Raises

        - ValueError: If any policy ID is empty or not a string
        """
        if not v:
            raise ValueError("policy_ids must contain at least one policy ID")
        for policy_id in v:
            if not isinstance(policy_id, str) or not policy_id.strip():
                raise ValueError(f"Invalid policy ID: {policy_id!r}. Must be a non-empty string.")
        return v

    def to_request_dict(self) -> Dict[str, Any]:
        """
        Convert to API request dictionary with camelCase keys.

        ## Returns

        Dictionary suitable for JSON request body.

        ## Example

        ```python
        body = PolicyIds(policy_ids=["POLICY-123", "POLICY-456"])
        payload = body.to_request_dict()
        # {"policyIds": ["POLICY-123", "POLICY-456"]}
        ```
        """
        return self.model_dump(by_alias=True, exclude_none=True)
