# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
ND Manage Policies endpoint models.

This module contains endpoint definitions for policy-related operations
in the ND Manage API.

Endpoints covered:
- GET /fabrics/{fabricName}/policies - Get policies
- POST /fabrics/{fabricName}/policies - Create policies in bulk
- GET /fabrics/{fabricName}/policies/{policyId} - Get policy by ID
- PUT /fabrics/{fabricName}/policies/{policyId} - Update a policy
- POST /fabrics/{fabricName}/policyActions/markDelete - Mark-delete policies
- POST /fabrics/{fabricName}/policyActions/pushConfig - Push config to policies
- POST /fabrics/{fabricName}/policyActions/remove - Remove policies in bulk
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from typing import Literal, Optional

from ansible_collections.cisco.nd.plugins.module_utils.enums import HttpVerbEnum
from ansible_collections.cisco.nd.plugins.module_utils.ep.base_paths_manage import BasePath
from ansible_collections.cisco.nd.plugins.module_utils.ep.endpoint_mixins import FabricNameMixin, PolicyIdMixin
from ansible_collections.cisco.nd.plugins.module_utils.ep.query_params import (
    CompositeQueryParams,
    EndpointQueryParams,
    LuceneQueryParams,
)
from ansible_collections.cisco.nd.plugins.module_utils.pydantic_compat import (
    BaseModel,
    ConfigDict,
    Field,
)


# Common Pydantic config
COMMON_CONFIG = ConfigDict(validate_assignment=True)


# ============================================================================
# Query Parameters for GET /policies
# ============================================================================


class PoliciesEndpointParams(EndpointQueryParams):
    """
    # Summary

    Endpoint-specific query parameters for GET /policies endpoint.

    ## Description

    Based on manage.json OpenAPI spec, the GET /policies endpoint accepts
    only `clusterName` as a named query parameter (besides the Lucene
    params: filter, max, offset, sort).

    For filtering by switchId, templateName, etc., use the Lucene `filter`
    parameter on `LuceneQueryParams` instead. Example:
    `filter=switchId:FDO123 AND templateName:switch_freeform`

    ## Parameters

    - cluster_name → clusterName

    ## Usage

    ```python
    params = PoliciesEndpointParams(cluster_name="cluster1")
    query_string = params.to_query_string()
    # "clusterName=cluster1"
    ```
    """

    model_config = ConfigDict(extra="forbid")

    cluster_name: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Target cluster name for multi-cluster deployments",
    )


class PolicyMutationEndpointParams(EndpointQueryParams):
    """
    # Summary

    Endpoint-specific query parameters for policy mutation endpoints.

    ## Description

    Based on manage.json OpenAPI spec, the following mutation endpoints accept
    `clusterName` and `ticketId` as query parameters:

    - POST /policies (createPolicies)
    - PUT /policies/{policyId} (updatePolicy)
    - DELETE /policies/{policyId} (deletePolicy)
    - POST /policyActions/markDelete (executeMarkDeletePolicies)
    - POST /policyActions/remove (deletePoliciesForIds)

    ## Parameters

    - cluster_name → clusterName
    - ticket_id → ticketId

    ## Usage

    ```python
    params = PolicyMutationEndpointParams(
        cluster_name="cluster1",
        ticket_id="MyTicket1234"
    )
    query_string = params.to_query_string()
    # "clusterName=cluster1&ticketId=MyTicket1234"
    ```
    """

    model_config = ConfigDict(extra="forbid")

    cluster_name: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Target cluster name for multi-cluster deployments",
    )
    ticket_id: Optional[str] = Field(
        default=None,
        min_length=1,
        max_length=64,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_-]+$",
        description="Change Control Ticket Id",
    )


class PolicyPushConfigEndpointParams(EndpointQueryParams):
    """
    # Summary

    Endpoint-specific query parameters for pushConfig endpoint.

    ## Description

    Based on manage.json OpenAPI spec, POST /policyActions/pushConfig
    accepts only `clusterName` (no ticketId).

    ## Parameters

    - cluster_name → clusterName

    ## Usage

    ```python
    params = PolicyPushConfigEndpointParams(cluster_name="cluster1")
    query_string = params.to_query_string()
    # "clusterName=cluster1"
    ```
    """

    model_config = ConfigDict(extra="forbid")

    cluster_name: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Target cluster name for multi-cluster deployments",
    )


# ============================================================================
# GET /fabrics/{fabricName}/policies
# GET /fabrics/{fabricName}/policies/{policyId}
# ============================================================================


class EpApiV1ManagePoliciesGet(FabricNameMixin, PolicyIdMixin, BaseModel):
    """
    # Summary

    ND Manage Policies GET Endpoint

    ## Description

    Retrieve policies from a fabric. Supports querying all policies,
    a specific policy by ID, or filtered results.

    ## Path

    - /api/v1/manage/fabrics/{fabricName}/policies
    - /api/v1/manage/fabrics/{fabricName}/policies/{policyId}

    ## Verb

    - GET

    ## Usage

    ```python
    # Get all policies for a fabric
    request = EpApiV1ManagePoliciesGet()
    request.fabric_name = "my-fabric"
    path = request.path
    verb = request.verb

    # Get specific policy by ID
    request = EpApiV1ManagePoliciesGet()
    request.fabric_name = "my-fabric"
    request.policy_id = "POLICY-12345"
    path = request.path

    # Get policies filtered by switchId and templateName (Lucene filter)
    request = EpApiV1ManagePoliciesGet()
    request.fabric_name = "my-fabric"
    request.lucene_params.filter = "switchId:FDO123 AND templateName:switch_freeform"
    request.lucene_params.max = 100
    path = request.path

    # Get policies for a specific cluster
    request = EpApiV1ManagePoliciesGet()
    request.fabric_name = "my-fabric"
    request.endpoint_params.cluster_name = "cluster1"
    path = request.path
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpApiV1ManagePoliciesGet"] = Field(
        default="EpApiV1ManagePoliciesGet",
        description="Class name for backward compatibility",
    )
    endpoint_params: PoliciesEndpointParams = Field(
        default_factory=PoliciesEndpointParams,
        description="Endpoint-specific query parameters",
    )
    lucene_params: LuceneQueryParams = Field(
        default_factory=LuceneQueryParams,
        description="Lucene-style filtering parameters (max, offset, sort, filter)",
    )

    @property
    def path(self) -> str:
        """Build the endpoint path with optional query string."""
        if self.fabric_name is None:
            raise ValueError("fabric_name must be set before accessing path")

        # Build base path
        if self.policy_id:
            base_path = BasePath.nd_manage_fabric_policies(self.fabric_name, self.policy_id)
        else:
            base_path = BasePath.nd_manage_fabric_policies(self.fabric_name)

        # Add query string if parameters are set
        composite = CompositeQueryParams()
        composite.add(self.endpoint_params)
        composite.add(self.lucene_params)

        query_string = composite.to_query_string()
        if query_string:
            return f"{base_path}?{query_string}"
        return base_path

    @property
    def verb(self) -> HttpVerbEnum:
        """Return the HTTP verb for this endpoint."""
        return HttpVerbEnum.GET


# ============================================================================
# POST /fabrics/{fabricName}/policies
# ============================================================================


class EpApiV1ManagePoliciesPost(FabricNameMixin, BaseModel):
    """
    # Summary

    ND Manage Policies POST Endpoint

    ## Description

    Create one or more policies in a fabric.

    ## Path

    - /api/v1/manage/fabrics/{fabricName}/policies

    ## Verb

    - POST

    ## Usage

    ```python
    request = EpApiV1ManagePoliciesPost()
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
        "policies": [
            {
                "switchId": "FDO25031SY4",
                "templateName": "feature_enable",
                "entityType": "switch",
                "entityName": "SWITCH",
                "templateInputs": {"featureName": "lacp"},
                "priority": 500
            }
        ]
    }
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpApiV1ManagePoliciesPost"] = Field(
        default="EpApiV1ManagePoliciesPost",
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
        base_path = BasePath.nd_manage_fabric_policies(self.fabric_name)
        query_string = self.endpoint_params.to_query_string()
        if query_string:
            return f"{base_path}?{query_string}"
        return base_path

    @property
    def verb(self) -> HttpVerbEnum:
        """Return the HTTP verb for this endpoint."""
        return HttpVerbEnum.POST


# ============================================================================
# PUT /fabrics/{fabricName}/policies/{policyId}
# ============================================================================


class EpApiV1ManagePoliciesPut(FabricNameMixin, PolicyIdMixin, BaseModel):
    """
    # Summary

    ND Manage Policies PUT Endpoint

    ## Description

    Update a specific policy in a fabric.

    ## Path

    - /api/v1/manage/fabrics/{fabricName}/policies/{policyId}

    ## Verb

    - PUT

    ## Usage

    ```python
    request = EpApiV1ManagePoliciesPut()
    request.fabric_name = "my-fabric"
    request.policy_id = "POLICY-12345"

    path = request.path
    verb = request.verb
    ```

    ## Query Parameters (per manage.json)

    - clusterName (optional): Target cluster in multi-cluster deployment
    - ticketId (optional): Change Control Ticket Id

    ## Request Body Example

    ```json
    {
        "switchId": "FDO25031SY4",
        "templateName": "feature_enable",
        "entityType": "switch",
        "entityName": "SWITCH",
        "templateInputs": {"featureName": "lacp"},
        "priority": 100
    }
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpApiV1ManagePoliciesPut"] = Field(
        default="EpApiV1ManagePoliciesPut",
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
        if self.policy_id is None:
            raise ValueError("policy_id must be set before accessing path")
        base_path = BasePath.nd_manage_fabric_policies(self.fabric_name, self.policy_id)
        query_string = self.endpoint_params.to_query_string()
        if query_string:
            return f"{base_path}?{query_string}"
        return base_path

    @property
    def verb(self) -> HttpVerbEnum:
        """Return the HTTP verb for this endpoint."""
        return HttpVerbEnum.PUT


# ============================================================================
# POST /fabrics/{fabricName}/policyActions/markDelete
# ============================================================================


class EpApiV1ManagePolicyActionsMarkDelete(FabricNameMixin, BaseModel):
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
    request = EpApiV1ManagePolicyActionsMarkDelete()
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

    class_name: Literal["EpApiV1ManagePolicyActionsMarkDelete"] = Field(
        default="EpApiV1ManagePolicyActionsMarkDelete",
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


class EpApiV1ManagePolicyActionsPushConfig(FabricNameMixin, BaseModel):
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
    request = EpApiV1ManagePolicyActionsPushConfig()
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

    class_name: Literal["EpApiV1ManagePolicyActionsPushConfig"] = Field(
        default="EpApiV1ManagePolicyActionsPushConfig",
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


class EpApiV1ManagePolicyActionsRemove(FabricNameMixin, BaseModel):
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
    request = EpApiV1ManagePolicyActionsRemove()
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

    class_name: Literal["EpApiV1ManagePolicyActionsRemove"] = Field(
        default="EpApiV1ManagePolicyActionsRemove",
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
