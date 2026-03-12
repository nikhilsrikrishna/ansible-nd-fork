# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pydantic model for policy bulk-action request bodies.

This module provides ``PolicyIds``, the request body used by all three
policy action endpoints:

- POST /api/v1/manage/fabrics/{fabricName}/policyActions/markDelete
- POST /api/v1/manage/fabrics/{fabricName}/policyActions/pushConfig
- POST /api/v1/manage/fabrics/{fabricName}/policyActions/remove

## Schema origin (manage.json)

- ``PolicyIds`` ← ``policyActions`` schema
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from typing import Any, Dict, List

from ansible_collections.cisco.nd.plugins.module_utils.common.pydantic_compat import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


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
