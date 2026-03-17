# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
ND Manage Policy Actions endpoint models.

This module contains endpoint definitions for policy action operations
in the ND Manage API.

Endpoints covered:
- POST /fabrics/{fabricName}/policyActions/markDelete - Mark-delete policies
- POST /fabrics/{fabricName}/policyActions/pushConfig - Push config to policies
- POST /fabrics/{fabricName}/policyActions/remove - Remove policies in bulk
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from typing import Literal

from ansible_collections.cisco.nd.plugins.module_utils.endpoints.mixins import (
    FabricNameMixin,
)
from ansible_collections.cisco.nd.plugins.module_utils.endpoints.v1.base_paths_manage import (
    BasePath,
)
from ansible_collections.cisco.nd.plugins.module_utils.endpoints.v1.manage.nd_manage_policies.query_params import (
    PolicyMutationEndpointParams,
    PolicyPushConfigEndpointParams,
)
from ansible_collections.cisco.nd.plugins.module_utils.enums import HttpVerbEnum
from ansible_collections.cisco.nd.plugins.module_utils.common.pydantic_compat import (
    BaseModel,
    ConfigDict,
    Field,
)


# Common Pydantic config
COMMON_CONFIG = ConfigDict(validate_assignment=True)


# ============================================================================
# POST /fabrics/{fabricName}/policyActions/markDelete
# ============================================================================


class EpManagePolicyActionsMarkDeletePost(FabricNameMixin, BaseModel):
    """
    # Summary

    ND Manage Policy Actions - Mark Delete Endpoint

    ## Description

    Mark-delete policies in bulk. This flags policies for deletion
    without immediately removing them.

    ## Path

    - /api/v1/manage/fabrics/{fabricName}/policyActions/markDelete

    ## Verb

    - POST

    ## Usage

    ```python
    request = EpManagePolicyActionsMarkDeletePost()
    request.fabric_name = "my-fabric"

    path = request.path
    verb = request.verb
    ```

    ## Query Parameters (per manage.json)

    - clusterName (optional): Target cluster in multi-cluster deployment
    - ticketId (optional): Change Control Ticket Id

    ## Request Body Example

    ```json
    {
        "policyIds": ["POLICY-121110", "POLICY-121120"]
    }
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpManagePolicyActionsMarkDeletePost"] = Field(
        default="EpManagePolicyActionsMarkDeletePost",
        description="Class name for backward compatibility",
    )
    endpoint_params: PolicyMutationEndpointParams = Field(
        default_factory=PolicyMutationEndpointParams,
        description="Query parameters: clusterName, ticketId",
    )

    @property
    def path(self) -> str:
        """Build the endpoint path with optional query string."""
        if self.fabric_name is None:
            raise ValueError("fabric_name must be set before accessing path")
        base_path = BasePath.nd_manage_fabric_policy_actions(self.fabric_name, "markDelete")
        query_string = self.endpoint_params.to_query_string()
        if query_string:
            return f"{base_path}?{query_string}"
        return base_path

    @property
    def verb(self) -> HttpVerbEnum:
        """Return the HTTP verb for this endpoint."""
        return HttpVerbEnum.POST


# ============================================================================
# POST /fabrics/{fabricName}/policyActions/pushConfig
# ============================================================================


class EpManagePolicyActionsPushConfigPost(FabricNameMixin, BaseModel):
    """
    # Summary

    ND Manage Policy Actions - Push Config Endpoint

    ## Description

    Push configuration for policies in bulk. This deploys the policy
    configurations to the target switches.

    ## Path

    - /api/v1/manage/fabrics/{fabricName}/policyActions/pushConfig

    ## Verb

    - POST

    ## Usage

    ```python
    request = EpManagePolicyActionsPushConfigPost()
    request.fabric_name = "my-fabric"

    path = request.path
    verb = request.verb
    ```

    ## Query Parameters (per manage.json)

    - clusterName (optional): Target cluster in multi-cluster deployment
    - NOTE: pushConfig does NOT accept ticketId per manage.json spec

    ## Request Body Example

    ```json
    {
        "policyIds": ["POLICY-121110", "POLICY-121120"]
    }
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpManagePolicyActionsPushConfigPost"] = Field(
        default="EpManagePolicyActionsPushConfigPost",
        description="Class name for backward compatibility",
    )
    endpoint_params: PolicyPushConfigEndpointParams = Field(
        default_factory=PolicyPushConfigEndpointParams,
        description="Query parameters: clusterName only (no ticketId)",
    )

    @property
    def path(self) -> str:
        """Build the endpoint path with optional query string."""
        if self.fabric_name is None:
            raise ValueError("fabric_name must be set before accessing path")
        base_path = BasePath.nd_manage_fabric_policy_actions(self.fabric_name, "pushConfig")
        query_string = self.endpoint_params.to_query_string()
        if query_string:
            return f"{base_path}?{query_string}"
        return base_path

    @property
    def verb(self) -> HttpVerbEnum:
        """Return the HTTP verb for this endpoint."""
        return HttpVerbEnum.POST


# ============================================================================
# POST /fabrics/{fabricName}/policyActions/remove
# ============================================================================


class EpManagePolicyActionsRemovePost(FabricNameMixin, BaseModel):
    """
    # Summary

    ND Manage Policy Actions - Remove Endpoint

    ## Description

    Delete/remove policies in bulk. This permanently removes the
    specified policies from the fabric.

    ## Path

    - /api/v1/manage/fabrics/{fabricName}/policyActions/remove

    ## Verb

    - POST

    ## Usage

    ```python
    request = EpManagePolicyActionsRemovePost()
    request.fabric_name = "my-fabric"

    path = request.path
    verb = request.verb
    ```

    ## Query Parameters (per manage.json)

    - clusterName (optional): Target cluster in multi-cluster deployment
    - ticketId (optional): Change Control Ticket Id

    ## Request Body Example

    ```json
    {
        "policyIds": ["POLICY-121110", "POLICY-121120"]
    }
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpManagePolicyActionsRemovePost"] = Field(
        default="EpManagePolicyActionsRemovePost",
        description="Class name for backward compatibility",
    )
    endpoint_params: PolicyMutationEndpointParams = Field(
        default_factory=PolicyMutationEndpointParams,
        description="Query parameters: clusterName, ticketId",
    )

    @property
    def path(self) -> str:
        """Build the endpoint path with optional query string."""
        if self.fabric_name is None:
            raise ValueError("fabric_name must be set before accessing path")
        base_path = BasePath.nd_manage_fabric_policy_actions(self.fabric_name, "remove")
        query_string = self.endpoint_params.to_query_string()
        if query_string:
            return f"{base_path}?{query_string}"
        return base_path

    @property
    def verb(self) -> HttpVerbEnum:
        """Return the HTTP verb for this endpoint."""
        return HttpVerbEnum.POST
