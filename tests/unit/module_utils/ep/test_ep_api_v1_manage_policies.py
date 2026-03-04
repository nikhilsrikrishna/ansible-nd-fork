# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems

# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Unit tests for ep_api_v1_manage_policies.py

Tests the ND Manage Policies endpoint classes
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name

import pytest  # pylint: disable=unused-import
from ansible_collections.cisco.nd.plugins.module_utils.enums import HttpVerbEnum
from ansible_collections.cisco.nd.plugins.module_utils.ep.ep_api_v1_manage_policies import (
    EpApiV1ManagePoliciesDelete,
    EpApiV1ManagePoliciesGet,
    EpApiV1ManagePoliciesPost,
    EpApiV1ManagePoliciesPut,
    EpApiV1ManagePolicyActionsMarkDelete,
    EpApiV1ManagePolicyActionsPushConfig,
    EpApiV1ManagePolicyActionsRemove,
    PoliciesEndpointParams,
    PolicyMutationEndpointParams,
    PolicyPushConfigEndpointParams,
)
from ansible_collections.cisco.nd.tests.unit.module_utils.common_utils import does_not_raise


# =============================================================================
# Test: PoliciesEndpointParams
# =============================================================================


def test_ep_policies_params_00010():
    """
    # Summary

    Verify PoliciesEndpointParams default values

    ## Test

    - cluster_name defaults to None
    - No other endpoint-specific params exist (serial_number, template_name,
      entity_name, entity_type belong in Lucene filter per manage.json spec)

    ## Classes and Methods

    - PoliciesEndpointParams.__init__()
    """
    with does_not_raise():
        params = PoliciesEndpointParams()
    assert params.cluster_name is None


def test_ep_policies_params_00020():
    """
    # Summary

    Verify PoliciesEndpointParams cluster_name can be set

    ## Test

    - cluster_name can be set to a string value

    ## Classes and Methods

    - PoliciesEndpointParams.__init__()
    """
    with does_not_raise():
        params = PoliciesEndpointParams(cluster_name="cluster1")
    assert params.cluster_name == "cluster1"


def test_ep_policies_params_00030():
    """
    # Summary

    Verify PoliciesEndpointParams generates correct query string

    ## Test

    - to_query_string() returns correct format with cluster_name set
    - Converts snake_case to camelCase

    ## Classes and Methods

    - PoliciesEndpointParams.to_query_string()
    """
    with does_not_raise():
        params = PoliciesEndpointParams(cluster_name="cluster1")
        result = params.to_query_string()
    assert "clusterName=cluster1" in result
    assert "cluster_name" not in result


def test_ep_policies_params_00040():
    """
    # Summary

    Verify PoliciesEndpointParams empty query string

    ## Test

    - to_query_string() returns empty string when no params set

    ## Classes and Methods

    - PoliciesEndpointParams.to_query_string()
    """
    with does_not_raise():
        params = PoliciesEndpointParams()
        result = params.to_query_string()
    assert result == ""


def test_ep_policies_params_00050():
    """
    # Summary

    Verify PoliciesEndpointParams rejects non-spec fields

    ## Test

    - serial_number, template_name, entity_name, entity_type are NOT
      valid endpoint params per manage.json. They should be passed via
      the Lucene filter parameter instead.

    ## Classes and Methods

    - PoliciesEndpointParams.__init__()
    """
    with pytest.raises(Exception):
        PoliciesEndpointParams(serial_number="FDO123")
    with pytest.raises(Exception):
        PoliciesEndpointParams(template_name="switch_freeform")
    with pytest.raises(Exception):
        PoliciesEndpointParams(entity_name="SWITCH")
    with pytest.raises(Exception):
        PoliciesEndpointParams(entity_type="switch")


# =============================================================================
# Test: PolicyMutationEndpointParams
# =============================================================================


def test_ep_mutation_params_00060():
    """
    # Summary

    Verify PolicyMutationEndpointParams default values

    ## Test

    - cluster_name defaults to None
    - ticket_id defaults to None

    ## Classes and Methods

    - PolicyMutationEndpointParams.__init__()
    """
    with does_not_raise():
        params = PolicyMutationEndpointParams()
    assert params.cluster_name is None
    assert params.ticket_id is None


def test_ep_mutation_params_00061():
    """
    # Summary

    Verify PolicyMutationEndpointParams query string with both params

    ## Test

    - to_query_string() returns correct format with both cluster_name and ticket_id

    ## Classes and Methods

    - PolicyMutationEndpointParams.to_query_string()
    """
    with does_not_raise():
        params = PolicyMutationEndpointParams(
            cluster_name="cluster1",
            ticket_id="MyTicket1234",
        )
        result = params.to_query_string()
    assert "clusterName=cluster1" in result
    assert "ticketId=MyTicket1234" in result


def test_ep_mutation_params_00062():
    """
    # Summary

    Verify PolicyMutationEndpointParams ticket_id only

    ## Test

    - to_query_string() returns correct format with only ticket_id set

    ## Classes and Methods

    - PolicyMutationEndpointParams.to_query_string()
    """
    with does_not_raise():
        params = PolicyMutationEndpointParams(ticket_id="Ticket99")
        result = params.to_query_string()
    assert result == "ticketId=Ticket99"
    assert "clusterName" not in result


def test_ep_mutation_params_00063():
    """
    # Summary

    Verify PolicyMutationEndpointParams ticket_id validation

    ## Test

    - ticket_id must match pattern ^[a-zA-Z][a-zA-Z0-9_-]+$
    - ticket_id cannot start with a number

    ## Classes and Methods

    - PolicyMutationEndpointParams.__init__()
    """
    with pytest.raises(Exception):
        PolicyMutationEndpointParams(ticket_id="123Invalid")
    with pytest.raises(Exception):
        PolicyMutationEndpointParams(ticket_id="")


def test_ep_mutation_params_00064():
    """
    # Summary

    Verify PolicyMutationEndpointParams rejects non-spec fields

    ## Test

    - extra="forbid" prevents non-spec fields

    ## Classes and Methods

    - PolicyMutationEndpointParams.__init__()
    """
    with pytest.raises(Exception):
        PolicyMutationEndpointParams(serial_number="FDO123")
    with pytest.raises(Exception):
        PolicyMutationEndpointParams(template_name="switch_freeform")


def test_ep_mutation_params_00065():
    """
    # Summary

    Verify PolicyMutationEndpointParams empty query string

    ## Test

    - to_query_string() returns empty string when no params set

    ## Classes and Methods

    - PolicyMutationEndpointParams.to_query_string()
    """
    with does_not_raise():
        params = PolicyMutationEndpointParams()
        result = params.to_query_string()
    assert result == ""


# =============================================================================
# Test: PolicyPushConfigEndpointParams
# =============================================================================


def test_ep_push_config_params_00070():
    """
    # Summary

    Verify PolicyPushConfigEndpointParams default values

    ## Test

    - cluster_name defaults to None
    - NO ticket_id field (pushConfig does not accept ticketId per spec)

    ## Classes and Methods

    - PolicyPushConfigEndpointParams.__init__()
    """
    with does_not_raise():
        params = PolicyPushConfigEndpointParams()
    assert params.cluster_name is None


def test_ep_push_config_params_00071():
    """
    # Summary

    Verify PolicyPushConfigEndpointParams rejects ticketId

    ## Test

    - pushConfig endpoint does NOT accept ticketId per manage.json spec
    - extra="forbid" ensures this is enforced

    ## Classes and Methods

    - PolicyPushConfigEndpointParams.__init__()
    """
    with pytest.raises(Exception):
        PolicyPushConfigEndpointParams(ticket_id="MyTicket1234")


def test_ep_push_config_params_00072():
    """
    # Summary

    Verify PolicyPushConfigEndpointParams query string with cluster_name

    ## Test

    - to_query_string() returns correct format with cluster_name

    ## Classes and Methods

    - PolicyPushConfigEndpointParams.to_query_string()
    """
    with does_not_raise():
        params = PolicyPushConfigEndpointParams(cluster_name="cluster1")
        result = params.to_query_string()
    assert result == "clusterName=cluster1"


# =============================================================================
# Test: EpApiV1ManagePoliciesGet
# =============================================================================


def test_ep_policies_get_00100():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet basic instantiation

    ## Test

    - Instance can be created
    - verb is GET
    - fabric_name defaults to None
    - policy_id defaults to None

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.__init__()
    - EpApiV1ManagePoliciesGet.verb
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
    assert instance.verb == HttpVerbEnum.GET
    assert instance.fabric_name is None
    assert instance.policy_id is None


def test_ep_policies_get_00110():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet raises ValueError when fabric_name not set

    ## Test

    - Accessing path without fabric_name raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    """
    instance = EpApiV1ManagePoliciesGet()
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "fabric_name must be set" in str(exc_info.value)


def test_ep_policies_get_00120():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet path with fabric_name only

    ## Test

    - path returns correct base path for listing all policies

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
        instance.fabric_name = "prod-fabric"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policies"


def test_ep_policies_get_00130():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet path with fabric_name and policy_id

    ## Test

    - path returns correct path for getting specific policy

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
        instance.fabric_name = "prod-fabric"
        instance.policy_id = "POLICY-121110"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policies/POLICY-121110"


def test_ep_policies_get_00140():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet path with clusterName query parameter

    ## Test

    - path includes clusterName query string when endpoint_params.cluster_name is set

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    - EpApiV1ManagePoliciesGet.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
        instance.fabric_name = "prod-fabric"
        instance.endpoint_params.cluster_name = "cluster1"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policies?clusterName=cluster1"


def test_ep_policies_get_00150():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet path with lucene parameters

    ## Test

    - path includes lucene params (max, offset) in query string

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    - EpApiV1ManagePoliciesGet.lucene_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
        instance.fabric_name = "prod-fabric"
        instance.lucene_params.max = 100
        instance.lucene_params.offset = 0
        result = instance.path
    assert "max=100" in result
    assert "offset=0" in result


def test_ep_policies_get_00160():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet path with mixed parameters

    ## Test

    - path includes both endpoint_params (clusterName) and lucene_params

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
        instance.fabric_name = "prod-fabric"
        instance.endpoint_params.cluster_name = "cluster1"
        instance.lucene_params.max = 50
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policies?" in result
    assert "clusterName=cluster1" in result
    assert "max=50" in result


def test_ep_policies_get_00165():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet path with Lucene filter for switchId and templateName

    ## Test

    - Filtering by switchId and templateName uses lucene_params.filter
      (not endpoint_params, per manage.json spec)

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    - EpApiV1ManagePoliciesGet.lucene_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
        instance.fabric_name = "prod-fabric"
        instance.lucene_params.filter = "switchId:FDO123 AND templateName:switch_freeform"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policies?" in result
    assert "filter=" in result
    # URL-encoded Lucene filter
    assert "switchId" in result
    assert "templateName" in result


def test_ep_policies_get_00167():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet path with all Lucene params

    ## Test

    - path includes filter, max, offset, sort from lucene_params

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.path
    - EpApiV1ManagePoliciesGet.lucene_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
        instance.fabric_name = "prod-fabric"
        instance.lucene_params.filter = "switchId:FDO123"
        instance.lucene_params.max = 100
        instance.lucene_params.offset = 0
        instance.lucene_params.sort = "priority:desc"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policies?" in result
    assert "filter=" in result
    assert "max=100" in result
    assert "offset=0" in result
    assert "sort=" in result


def test_ep_policies_get_00170():
    """
    # Summary

    Verify EpApiV1ManagePoliciesGet class_name field

    ## Test

    - class_name is set correctly for backward compatibility

    ## Classes and Methods

    - EpApiV1ManagePoliciesGet.class_name
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesGet()
    assert instance.class_name == "EpApiV1ManagePoliciesGet"


# =============================================================================
# Test: EpApiV1ManagePoliciesPost
# =============================================================================


def test_ep_policies_post_00200():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPost basic instantiation

    ## Test

    - Instance can be created
    - verb is POST
    - fabric_name defaults to None

    ## Classes and Methods

    - EpApiV1ManagePoliciesPost.__init__()
    - EpApiV1ManagePoliciesPost.verb
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPost()
    assert instance.verb == HttpVerbEnum.POST
    assert instance.fabric_name is None


def test_ep_policies_post_00210():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPost raises ValueError when fabric_name not set

    ## Test

    - Accessing path without fabric_name raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePoliciesPost.path
    """
    instance = EpApiV1ManagePoliciesPost()
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "fabric_name must be set" in str(exc_info.value)


def test_ep_policies_post_00220():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPost path with fabric_name

    ## Test

    - path returns correct path for creating policies

    ## Classes and Methods

    - EpApiV1ManagePoliciesPost.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPost()
        instance.fabric_name = "prod-fabric"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policies"


def test_ep_policies_post_00230():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPost class_name field

    ## Test

    - class_name is set correctly for backward compatibility

    ## Classes and Methods

    - EpApiV1ManagePoliciesPost.class_name
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPost()
    assert instance.class_name == "EpApiV1ManagePoliciesPost"


def test_ep_policies_post_00240():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPost path with ticketId query parameter

    ## Test

    - path includes ticketId query string when endpoint_params.ticket_id is set
    - Per manage.json spec: POST /policies accepts clusterName and ticketId

    ## Classes and Methods

    - EpApiV1ManagePoliciesPost.path
    - EpApiV1ManagePoliciesPost.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPost()
        instance.fabric_name = "prod-fabric"
        instance.endpoint_params.ticket_id = "MyTicket1234"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policies?" in result
    assert "ticketId=MyTicket1234" in result


def test_ep_policies_post_00245():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPost path with clusterName and ticketId

    ## Test

    - path includes both clusterName and ticketId when both are set

    ## Classes and Methods

    - EpApiV1ManagePoliciesPost.path
    - EpApiV1ManagePoliciesPost.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPost()
        instance.fabric_name = "prod-fabric"
        instance.endpoint_params.cluster_name = "cluster1"
        instance.endpoint_params.ticket_id = "MyTicket1234"
        result = instance.path
    assert "clusterName=cluster1" in result
    assert "ticketId=MyTicket1234" in result


# =============================================================================
# Test: EpApiV1ManagePoliciesPut
# =============================================================================


def test_ep_policies_put_00300():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPut basic instantiation

    ## Test

    - Instance can be created
    - verb is PUT
    - fabric_name defaults to None
    - policy_id defaults to None

    ## Classes and Methods

    - EpApiV1ManagePoliciesPut.__init__()
    - EpApiV1ManagePoliciesPut.verb
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPut()
    assert instance.verb == HttpVerbEnum.PUT
    assert instance.fabric_name is None
    assert instance.policy_id is None


def test_ep_policies_put_00310():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPut raises ValueError when fabric_name not set

    ## Test

    - Accessing path without fabric_name raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePoliciesPut.path
    """
    instance = EpApiV1ManagePoliciesPut()
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "fabric_name must be set" in str(exc_info.value)


def test_ep_policies_put_00320():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPut raises ValueError when policy_id not set

    ## Test

    - Accessing path without policy_id raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePoliciesPut.path
    """
    instance = EpApiV1ManagePoliciesPut()
    instance.fabric_name = "prod-fabric"
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "policy_id must be set" in str(exc_info.value)


def test_ep_policies_put_00330():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPut path with fabric_name and policy_id

    ## Test

    - path returns correct path for updating a policy

    ## Classes and Methods

    - EpApiV1ManagePoliciesPut.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPut()
        instance.fabric_name = "prod-fabric"
        instance.policy_id = "POLICY-121110"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policies/POLICY-121110"


def test_ep_policies_put_00340():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPut class_name field

    ## Test

    - class_name is set correctly for backward compatibility

    ## Classes and Methods

    - EpApiV1ManagePoliciesPut.class_name
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPut()
    assert instance.class_name == "EpApiV1ManagePoliciesPut"


def test_ep_policies_put_00350():
    """
    # Summary

    Verify EpApiV1ManagePoliciesPut path with ticketId query parameter

    ## Test

    - path includes ticketId query string when endpoint_params.ticket_id is set
    - Per manage.json spec: PUT /policies/{policyId} accepts clusterName and ticketId

    ## Classes and Methods

    - EpApiV1ManagePoliciesPut.path
    - EpApiV1ManagePoliciesPut.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesPut()
        instance.fabric_name = "prod-fabric"
        instance.policy_id = "POLICY-121110"
        instance.endpoint_params.ticket_id = "ChangeReq42"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policies/POLICY-121110?" in result
    assert "ticketId=ChangeReq42" in result


# =============================================================================
# Test: EpApiV1ManagePoliciesDelete
# =============================================================================


def test_ep_policies_delete_00360():
    """
    # Summary

    Verify EpApiV1ManagePoliciesDelete basic instantiation

    ## Test

    - Instance can be created
    - verb is DELETE
    - fabric_name defaults to None
    - policy_id defaults to None

    ## Classes and Methods

    - EpApiV1ManagePoliciesDelete.__init__()
    - EpApiV1ManagePoliciesDelete.verb
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesDelete()
    assert instance.verb == HttpVerbEnum.DELETE
    assert instance.fabric_name is None
    assert instance.policy_id is None


def test_ep_policies_delete_00361():
    """
    # Summary

    Verify EpApiV1ManagePoliciesDelete raises ValueError when fabric_name not set

    ## Test

    - Accessing path without fabric_name raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePoliciesDelete.path
    """
    instance = EpApiV1ManagePoliciesDelete()
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "fabric_name must be set" in str(exc_info.value)


def test_ep_policies_delete_00362():
    """
    # Summary

    Verify EpApiV1ManagePoliciesDelete raises ValueError when policy_id not set

    ## Test

    - Accessing path without policy_id raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePoliciesDelete.path
    """
    instance = EpApiV1ManagePoliciesDelete()
    instance.fabric_name = "prod-fabric"
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "policy_id must be set" in str(exc_info.value)


def test_ep_policies_delete_00363():
    """
    # Summary

    Verify EpApiV1ManagePoliciesDelete path with fabric_name and policy_id

    ## Test

    - path returns correct path for deleting a policy

    ## Classes and Methods

    - EpApiV1ManagePoliciesDelete.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesDelete()
        instance.fabric_name = "prod-fabric"
        instance.policy_id = "POLICY-121110"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policies/POLICY-121110"


def test_ep_policies_delete_00364():
    """
    # Summary

    Verify EpApiV1ManagePoliciesDelete path with ticketId query parameter

    ## Test

    - path includes ticketId query string when endpoint_params.ticket_id is set
    - Per manage.json spec: DELETE /policies/{policyId} accepts clusterName and ticketId

    ## Classes and Methods

    - EpApiV1ManagePoliciesDelete.path
    - EpApiV1ManagePoliciesDelete.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesDelete()
        instance.fabric_name = "prod-fabric"
        instance.policy_id = "POLICY-121110"
        instance.endpoint_params.ticket_id = "ChangeReq42"
        instance.endpoint_params.cluster_name = "cluster1"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policies/POLICY-121110?" in result
    assert "ticketId=ChangeReq42" in result
    assert "clusterName=cluster1" in result


def test_ep_policies_delete_00365():
    """
    # Summary

    Verify EpApiV1ManagePoliciesDelete class_name field

    ## Test

    - class_name is set correctly for backward compatibility

    ## Classes and Methods

    - EpApiV1ManagePoliciesDelete.class_name
    """
    with does_not_raise():
        instance = EpApiV1ManagePoliciesDelete()
    assert instance.class_name == "EpApiV1ManagePoliciesDelete"


# =============================================================================
# Test: EpApiV1ManagePolicyActionsMarkDelete
# =============================================================================


def test_ep_policy_actions_mark_delete_00400():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsMarkDelete basic instantiation

    ## Test

    - Instance can be created
    - verb is POST
    - fabric_name defaults to None

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsMarkDelete.__init__()
    - EpApiV1ManagePolicyActionsMarkDelete.verb
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsMarkDelete()
    assert instance.verb == HttpVerbEnum.POST
    assert instance.fabric_name is None


def test_ep_policy_actions_mark_delete_00410():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsMarkDelete raises ValueError when fabric_name not set

    ## Test

    - Accessing path without fabric_name raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsMarkDelete.path
    """
    instance = EpApiV1ManagePolicyActionsMarkDelete()
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "fabric_name must be set" in str(exc_info.value)


def test_ep_policy_actions_mark_delete_00420():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsMarkDelete path with fabric_name

    ## Test

    - path returns correct path for markDelete action

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsMarkDelete.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsMarkDelete()
        instance.fabric_name = "prod-fabric"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policyActions/markDelete"


def test_ep_policy_actions_mark_delete_00430():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsMarkDelete class_name field

    ## Test

    - class_name is set correctly for backward compatibility

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsMarkDelete.class_name
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsMarkDelete()
    assert instance.class_name == "EpApiV1ManagePolicyActionsMarkDelete"


def test_ep_policy_actions_mark_delete_00440():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsMarkDelete path with ticketId

    ## Test

    - path includes ticketId query string when endpoint_params.ticket_id is set
    - Per manage.json spec: POST /policyActions/markDelete accepts clusterName and ticketId

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsMarkDelete.path
    - EpApiV1ManagePolicyActionsMarkDelete.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsMarkDelete()
        instance.fabric_name = "prod-fabric"
        instance.endpoint_params.ticket_id = "ChangeReq42"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policyActions/markDelete?" in result
    assert "ticketId=ChangeReq42" in result


# =============================================================================
# Test: EpApiV1ManagePolicyActionsPushConfig
# =============================================================================


def test_ep_policy_actions_push_config_00500():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsPushConfig basic instantiation

    ## Test

    - Instance can be created
    - verb is POST
    - fabric_name defaults to None

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsPushConfig.__init__()
    - EpApiV1ManagePolicyActionsPushConfig.verb
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsPushConfig()
    assert instance.verb == HttpVerbEnum.POST
    assert instance.fabric_name is None


def test_ep_policy_actions_push_config_00510():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsPushConfig raises ValueError when fabric_name not set

    ## Test

    - Accessing path without fabric_name raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsPushConfig.path
    """
    instance = EpApiV1ManagePolicyActionsPushConfig()
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "fabric_name must be set" in str(exc_info.value)


def test_ep_policy_actions_push_config_00520():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsPushConfig path with fabric_name

    ## Test

    - path returns correct path for pushConfig action

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsPushConfig.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsPushConfig()
        instance.fabric_name = "prod-fabric"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policyActions/pushConfig"


def test_ep_policy_actions_push_config_00530():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsPushConfig class_name field

    ## Test

    - class_name is set correctly for backward compatibility

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsPushConfig.class_name
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsPushConfig()
    assert instance.class_name == "EpApiV1ManagePolicyActionsPushConfig"


def test_ep_policy_actions_push_config_00540():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsPushConfig path with clusterName

    ## Test

    - path includes clusterName query string when endpoint_params.cluster_name is set
    - Per manage.json spec: POST /policyActions/pushConfig accepts clusterName only

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsPushConfig.path
    - EpApiV1ManagePolicyActionsPushConfig.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsPushConfig()
        instance.fabric_name = "prod-fabric"
        instance.endpoint_params.cluster_name = "cluster1"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policyActions/pushConfig?" in result
    assert "clusterName=cluster1" in result


def test_ep_policy_actions_push_config_00545():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsPushConfig rejects ticketId

    ## Test

    - pushConfig does NOT accept ticketId per manage.json spec
    - PolicyPushConfigEndpointParams has extra="forbid" to enforce this

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsPushConfig.endpoint_params
    - PolicyPushConfigEndpointParams.__init__()
    """
    with pytest.raises(Exception):
        PolicyPushConfigEndpointParams(ticket_id="MyTicket1234")


# =============================================================================
# Test: EpApiV1ManagePolicyActionsRemove
# =============================================================================


def test_ep_policy_actions_remove_00600():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsRemove basic instantiation

    ## Test

    - Instance can be created
    - verb is POST
    - fabric_name defaults to None

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsRemove.__init__()
    - EpApiV1ManagePolicyActionsRemove.verb
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsRemove()
    assert instance.verb == HttpVerbEnum.POST
    assert instance.fabric_name is None


def test_ep_policy_actions_remove_00610():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsRemove raises ValueError when fabric_name not set

    ## Test

    - Accessing path without fabric_name raises ValueError

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsRemove.path
    """
    instance = EpApiV1ManagePolicyActionsRemove()
    with pytest.raises(ValueError) as exc_info:
        _ = instance.path
    assert "fabric_name must be set" in str(exc_info.value)


def test_ep_policy_actions_remove_00620():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsRemove path with fabric_name

    ## Test

    - path returns correct path for remove action

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsRemove.path
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsRemove()
        instance.fabric_name = "prod-fabric"
        result = instance.path
    assert result == "/api/v1/manage/fabrics/prod-fabric/policyActions/remove"


def test_ep_policy_actions_remove_00630():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsRemove class_name field

    ## Test

    - class_name is set correctly for backward compatibility

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsRemove.class_name
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsRemove()
    assert instance.class_name == "EpApiV1ManagePolicyActionsRemove"


def test_ep_policy_actions_remove_00640():
    """
    # Summary

    Verify EpApiV1ManagePolicyActionsRemove path with ticketId

    ## Test

    - path includes ticketId query string when endpoint_params.ticket_id is set
    - Per manage.json spec: POST /policyActions/remove accepts clusterName and ticketId

    ## Classes and Methods

    - EpApiV1ManagePolicyActionsRemove.path
    - EpApiV1ManagePolicyActionsRemove.endpoint_params
    """
    with does_not_raise():
        instance = EpApiV1ManagePolicyActionsRemove()
        instance.fabric_name = "prod-fabric"
        instance.endpoint_params.ticket_id = "ChangeReq42"
        instance.endpoint_params.cluster_name = "cluster1"
        result = instance.path
    assert "/api/v1/manage/fabrics/prod-fabric/policyActions/remove?" in result
    assert "ticketId=ChangeReq42" in result
    assert "clusterName=cluster1" in result
