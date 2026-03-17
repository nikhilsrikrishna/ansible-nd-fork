# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
ND Manage Policies endpoint models.

This module contains endpoint definitions for policy CRUD operations
in the ND Manage API.

Endpoints covered:
- GET /fabrics/{fabricName}/policies - Get policies
- POST /fabrics/{fabricName}/policies - Create policies in bulk
- GET /fabrics/{fabricName}/policies/{policyId} - Get policy by ID
- PUT /fabrics/{fabricName}/policies/{policyId} - Update a policy
- DELETE /fabrics/{fabricName}/policies/{policyId} - Delete a policy
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from typing import Literal

from ansible_collections.cisco.nd.plugins.module_utils.endpoints.mixins import (
    FabricNameMixin,
    PolicyIdMixin,
)
from ansible_collections.cisco.nd.plugins.module_utils.endpoints.query_params import (
    CompositeQueryParams,
    LuceneQueryParams,
)
from ansible_collections.cisco.nd.plugins.module_utils.endpoints.v1.base_paths_manage import (
    BasePath,
)
from ansible_collections.cisco.nd.plugins.module_utils.endpoints.v1.nd_manage_policies.query_params import (
    PoliciesEndpointParams,
    PolicyMutationEndpointParams,
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
# GET /fabrics/{fabricName}/policies
# GET /fabrics/{fabricName}/policies/{policyId}
# ============================================================================


class EpManagePoliciesGet(FabricNameMixin, PolicyIdMixin, BaseModel):
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
    request = EpManagePoliciesGet()
    request.fabric_name = "my-fabric"
    path = request.path
    verb = request.verb

    # Get specific policy by ID
    request = EpManagePoliciesGet()
    request.fabric_name = "my-fabric"
    request.policy_id = "POLICY-12345"
    path = request.path

    # Get policies filtered by switchId and templateName (Lucene filter)
    request = EpManagePoliciesGet()
    request.fabric_name = "my-fabric"
    request.lucene_params.filter = "switchId:FDO123 AND templateName:switch_freeform"
    request.lucene_params.max = 100
    path = request.path

    # Get policies for a specific cluster
    request = EpManagePoliciesGet()
    request.fabric_name = "my-fabric"
    request.endpoint_params.cluster_name = "cluster1"
    path = request.path
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpManagePoliciesGet"] = Field(
        default="EpManagePoliciesGet",
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


class EpManagePoliciesPost(FabricNameMixin, BaseModel):
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
    request = EpManagePoliciesPost()
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

    class_name: Literal["EpManagePoliciesPost"] = Field(
        default="EpManagePoliciesPost",
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


class EpManagePoliciesPut(FabricNameMixin, PolicyIdMixin, BaseModel):
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
    request = EpManagePoliciesPut()
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

    class_name: Literal["EpManagePoliciesPut"] = Field(
        default="EpManagePoliciesPut",
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
# DELETE /fabrics/{fabricName}/policies/{policyId}
# ============================================================================


class EpManagePoliciesDelete(FabricNameMixin, PolicyIdMixin, BaseModel):
    """
    # Summary

    ND Manage Policies DELETE Endpoint

    ## Description

    Delete a specific policy from a fabric by its policy ID.

    ## Path

    - /api/v1/manage/fabrics/{fabricName}/policies/{policyId}

    ## Verb

    - DELETE

    ## Usage

    ```python
    request = EpManagePoliciesDelete()
    request.fabric_name = "my-fabric"
    request.policy_id = "POLICY-12345"

    path = request.path
    verb = request.verb
    ```

    ## Query Parameters (per manage.json)

    - clusterName (optional): Target cluster in multi-cluster deployment
    - ticketId (optional): Change Control Ticket Id
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpManagePoliciesDelete"] = Field(
        default="EpManagePoliciesDelete",
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
        return HttpVerbEnum.DELETE
