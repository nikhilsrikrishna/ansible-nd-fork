# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Base Pydantic model and enum for Policy API request bodies.

This module provides the foundational ``PolicyCreate`` model and its
``PolicyEntityType`` enum.  All other policy models that extend or wrap
``PolicyCreate`` live in separate files and import from here.

## Schema origin (manage.json)

- ``PolicyEntityType`` ← ``policyEntityType`` enum
- ``PolicyCreate``     ← ``createPolicy`` (extends ``createBasePolicy``)
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from enum import Enum
from typing import Any, Dict, Optional

from ansible_collections.cisco.nd.plugins.module_utils.common.pydantic_compat import (
    BaseModel,
    ConfigDict,
    Field,
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
# Policy Create Model (base for all CRUD body models)
# ============================================================================


class PolicyCreate(BaseModel):
    """
    Request body model for creating a single policy.

    ## Description

    Based on ``createPolicy`` schema from manage.json which extends
    ``createBasePolicy``.

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
    switch_id: str = Field(
        ...,
        alias="switchId",
        description="Switch serial number (e.g., FDO25031SY4)",
    )
    template_name: str = Field(
        ...,
        max_length=255,
        alias="templateName",
        description="Name of the policy template",
    )
    entity_type: PolicyEntityType = Field(
        ...,
        alias="entityType",
        description="Type of the entity (switch, configProfile, interface)",
    )
    entity_name: str = Field(
        ...,
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
