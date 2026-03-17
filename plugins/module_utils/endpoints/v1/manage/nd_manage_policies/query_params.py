# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Shared query parameter classes for policy endpoints.

This module provides query parameter models used across both
``policies.py`` (CRUD) and ``policy_actions.py`` (markDelete, pushConfig, remove).
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from typing import Optional

from ansible_collections.cisco.nd.plugins.module_utils.endpoints.query_params import (
    EndpointQueryParams,
)
from ansible_collections.cisco.nd.plugins.module_utils.common.pydantic_compat import (
    ConfigDict,
    Field,
)


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
