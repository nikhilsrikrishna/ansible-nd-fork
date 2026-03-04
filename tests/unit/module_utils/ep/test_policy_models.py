# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems

# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Unit tests for policy models

Tests the Pydantic models for policy request bodies:
- PolicyCreate
- PolicyCreateBulk
- PolicyUpdate
- PolicyIds
"""

from __future__ import absolute_import, annotations, division, print_function

__metaclass__ = type  # pylint: disable=invalid-name

import pytest  # pylint: disable=unused-import
from ansible_collections.cisco.nd.plugins.module_utils.models.policy import (
    PolicyCreate,
    PolicyCreateBulk,
    PolicyEntityType,
    PolicyIds,
    PolicyUpdate,
)
from ansible_collections.cisco.nd.tests.unit.module_utils.common_utils import does_not_raise


# =============================================================================
# Test: PolicyEntityType
# =============================================================================


def test_policy_entity_type_00010():
    """
    # Summary

    Verify PolicyEntityType enum values

    ## Test

    - SWITCH value is "switch"
    - CONFIG_PROFILE value is "configProfile"
    - INTERFACE value is "interface"

    ## Classes and Methods

    - PolicyEntityType
    """
    assert PolicyEntityType.SWITCH.value == "switch"
    assert PolicyEntityType.CONFIG_PROFILE.value == "configProfile"
    assert PolicyEntityType.INTERFACE.value == "interface"


# =============================================================================
# Test: PolicyCreate
# =============================================================================


def test_policy_create_00095():
    """
    # Summary

    Verify PolicyCreate requires mandatory fields

    ## Test

    - Creating PolicyCreate without required fields raises ValidationError

    ## Classes and Methods

    - PolicyCreate.__init__()
    """
    with pytest.raises(Exception):  # Pydantic ValidationError
        PolicyCreate()  # Missing all required fields


def test_policy_create_00096():
    """
    # Summary

    Verify PolicyCreate requires switch_id

    ## Test

    - Creating PolicyCreate without switch_id raises ValidationError

    ## Classes and Methods

    - PolicyCreate.__init__()
    """
    with pytest.raises(Exception):  # Pydantic ValidationError
        PolicyCreate(
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH"
        )


def test_policy_create_00097():
    """
    # Summary

    Verify PolicyCreate requires template_name

    ## Test

    - Creating PolicyCreate without template_name raises ValidationError

    ## Classes and Methods

    - PolicyCreate.__init__()
    """
    with pytest.raises(Exception):  # Pydantic ValidationError
        PolicyCreate(
            switch_id="FDO123",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH"
        )


def test_policy_create_00100():
    """
    # Summary

    Verify PolicyCreate basic instantiation with required fields

    ## Test

    - Instance can be created with required fields
    - Fields are set correctly

    ## Classes and Methods

    - PolicyCreate.__init__()
    """
    with does_not_raise():
        policy = PolicyCreate(
            switch_id="FDO25031SY4",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH"
        )
    assert policy.switch_id == "FDO25031SY4"
    assert policy.template_name == "feature_enable"
    assert policy.entity_type == PolicyEntityType.SWITCH
    assert policy.entity_name == "SWITCH"


def test_policy_create_00110():
    """
    # Summary

    Verify PolicyCreate default values for optional fields

    ## Test

    - priority defaults to 500
    - source defaults to empty string
    - description defaults to None
    - template_inputs defaults to None

    ## Classes and Methods

    - PolicyCreate.__init__()
    """
    with does_not_raise():
        policy = PolicyCreate(
            switch_id="FDO123",
            template_name="test",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH"
        )
    assert policy.priority == 500
    assert policy.source == ""
    assert policy.description is None
    assert policy.template_inputs is None


def test_policy_create_00120():
    """
    # Summary

    Verify PolicyCreate with all fields

    ## Test

    - All optional fields can be set

    ## Classes and Methods

    - PolicyCreate.__init__()
    """
    with does_not_raise():
        policy = PolicyCreate(
            switch_id="FDO25031SY4",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH",
            description="Test policy",
            priority=100,
            source="UNDERLAY",
            template_inputs={"featureName": "lacp"},
            secondary_entity_name="secondary",
            secondary_entity_type=PolicyEntityType.INTERFACE
        )
    assert policy.description == "Test policy"
    assert policy.priority == 100
    assert policy.source == "UNDERLAY"
    assert policy.template_inputs == {"featureName": "lacp"}
    assert policy.secondary_entity_name == "secondary"
    assert policy.secondary_entity_type == PolicyEntityType.INTERFACE


def test_policy_create_00130():
    """
    # Summary

    Verify PolicyCreate to_request_dict() with camelCase keys

    ## Test

    - to_request_dict() returns dictionary with camelCase keys
    - snake_case fields are converted properly

    ## Classes and Methods

    - PolicyCreate.to_request_dict()
    """
    with does_not_raise():
        policy = PolicyCreate(
            switch_id="FDO123",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH",
            template_inputs={"featureName": "lacp"}
        )
        result = policy.to_request_dict()
    # Verify camelCase keys
    assert "switchId" in result
    assert "templateName" in result
    assert "entityType" in result
    assert "entityName" in result
    assert "templateInputs" in result
    # Verify no snake_case keys
    assert "switch_id" not in result
    assert "template_name" not in result
    assert "entity_type" not in result
    assert "entity_name" not in result
    assert "template_inputs" not in result


def test_policy_create_00140():
    """
    # Summary

    Verify PolicyCreate to_request_dict() excludes None values

    ## Test

    - to_request_dict() excludes fields with None values

    ## Classes and Methods

    - PolicyCreate.to_request_dict()
    """
    with does_not_raise():
        policy = PolicyCreate(
            switch_id="FDO123",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH"
        )
        result = policy.to_request_dict()
    # Fields with None values should be excluded
    assert "description" not in result
    assert "templateInputs" not in result
    assert "secondaryEntityName" not in result
    assert "secondaryEntityType" not in result


def test_policy_create_00150():
    """
    # Summary

    Verify PolicyCreate to_request_dict() values

    ## Test

    - to_request_dict() returns correct values

    ## Classes and Methods

    - PolicyCreate.to_request_dict()
    """
    with does_not_raise():
        policy = PolicyCreate(
            switch_id="FDO25031SY4",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH",
            priority=100,
            description="Test"
        )
        result = policy.to_request_dict()
    assert result["switchId"] == "FDO25031SY4"
    assert result["templateName"] == "feature_enable"
    assert result["entityType"] == "switch"
    assert result["entityName"] == "SWITCH"
    assert result["priority"] == 100
    assert result["description"] == "Test"


def test_policy_create_00160():
    """
    # Summary

    Verify PolicyCreate for interface-level policy

    ## Test

    - entity_type can be set to INTERFACE
    - entity_name can be set to interface name

    ## Classes and Methods

    - PolicyCreate.__init__()
    """
    with does_not_raise():
        policy = PolicyCreate(
            switch_id="FDO25031SY4",
            template_name="int_trunk_host",
            entity_type=PolicyEntityType.INTERFACE,
            entity_name="Ethernet1/1",
            template_inputs={"ALLOWED_VLANS": "100-200"}
        )
    assert policy.entity_type == PolicyEntityType.INTERFACE
    assert policy.entity_name == "Ethernet1/1"


# =============================================================================
# Test: PolicyCreateBulk
# =============================================================================


def test_policy_create_bulk_00200():
    """
    # Summary

    Verify PolicyCreateBulk basic instantiation

    ## Test

    - Instance can be created with list of policies

    ## Classes and Methods

    - PolicyCreateBulk.__init__()
    """
    policy1 = PolicyCreate(
        switch_id="FDO123",
        template_name="feature_enable",
        entity_type=PolicyEntityType.SWITCH,
        entity_name="SWITCH"
    )
    policy2 = PolicyCreate(
        switch_id="FDO456",
        template_name="power_redundancy",
        entity_type=PolicyEntityType.SWITCH,
        entity_name="SWITCH"
    )
    with does_not_raise():
        bulk = PolicyCreateBulk(policies=[policy1, policy2])
    assert len(bulk.policies) == 2


def test_policy_create_bulk_00210():
    """
    # Summary

    Verify PolicyCreateBulk to_request_dict()

    ## Test

    - to_request_dict() returns dict with "policies" key
    - Each policy is converted to camelCase dict

    ## Classes and Methods

    - PolicyCreateBulk.to_request_dict()
    """
    policy = PolicyCreate(
        switch_id="FDO123",
        template_name="feature_enable",
        entity_type=PolicyEntityType.SWITCH,
        entity_name="SWITCH"
    )
    with does_not_raise():
        bulk = PolicyCreateBulk(policies=[policy])
        result = bulk.to_request_dict()
    assert "policies" in result
    assert isinstance(result["policies"], list)
    assert len(result["policies"]) == 1
    assert "switchId" in result["policies"][0]


def test_policy_create_bulk_00220():
    """
    # Summary

    Verify PolicyCreateBulk with multiple policies

    ## Test

    - to_request_dict() correctly serializes multiple policies

    ## Classes and Methods

    - PolicyCreateBulk.to_request_dict()
    """
    policy1 = PolicyCreate(
        switch_id="FDO123",
        template_name="feature_enable",
        entity_type=PolicyEntityType.SWITCH,
        entity_name="SWITCH"
    )
    policy2 = PolicyCreate(
        switch_id="FDO456",
        template_name="power_redundancy",
        entity_type=PolicyEntityType.SWITCH,
        entity_name="SWITCH"
    )
    with does_not_raise():
        bulk = PolicyCreateBulk(policies=[policy1, policy2])
        result = bulk.to_request_dict()
    assert len(result["policies"]) == 2
    assert result["policies"][0]["switchId"] == "FDO123"
    assert result["policies"][1]["switchId"] == "FDO456"


# =============================================================================
# Test: PolicyUpdate
# =============================================================================


def test_policy_update_00300():
    """
    # Summary

    Verify PolicyUpdate inherits from PolicyCreate

    ## Test

    - PolicyUpdate has all fields from PolicyCreate

    ## Classes and Methods

    - PolicyUpdate.__init__()
    """
    with does_not_raise():
        update = PolicyUpdate(
            switch_id="FDO25031SY4",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH",
            priority=100,
            description="Updated policy"
        )
    assert update.switch_id == "FDO25031SY4"
    assert update.template_name == "feature_enable"
    assert update.priority == 100
    assert update.description == "Updated policy"


def test_policy_update_00310():
    """
    # Summary

    Verify PolicyUpdate to_request_dict()

    ## Test

    - to_request_dict() works same as PolicyCreate

    ## Classes and Methods

    - PolicyUpdate.to_request_dict()
    """
    with does_not_raise():
        update = PolicyUpdate(
            switch_id="FDO123",
            template_name="feature_enable",
            entity_type=PolicyEntityType.SWITCH,
            entity_name="SWITCH"
        )
        result = update.to_request_dict()
    assert "switchId" in result
    assert result["switchId"] == "FDO123"


# =============================================================================
# Test: PolicyIds
# =============================================================================


def test_policy_ids_00400():
    """
    # Summary

    Verify PolicyIds basic instantiation

    ## Test

    - Instance can be created with list of policy IDs

    ## Classes and Methods

    - PolicyIds.__init__()
    """
    with does_not_raise():
        policy_ids = PolicyIds(policy_ids=["POLICY-121110", "POLICY-121120"])
    assert len(policy_ids.policy_ids) == 2
    assert "POLICY-121110" in policy_ids.policy_ids
    assert "POLICY-121120" in policy_ids.policy_ids


def test_policy_ids_00410():
    """
    # Summary

    Verify PolicyIds to_request_dict() with camelCase

    ## Test

    - to_request_dict() returns dict with "policyIds" key (camelCase)

    ## Classes and Methods

    - PolicyIds.to_request_dict()
    """
    with does_not_raise():
        policy_ids = PolicyIds(policy_ids=["POLICY-121110", "POLICY-121120"])
        result = policy_ids.to_request_dict()
    assert "policyIds" in result
    assert "policy_ids" not in result
    assert result["policyIds"] == ["POLICY-121110", "POLICY-121120"]


def test_policy_ids_00420():
    """
    # Summary

    Verify PolicyIds validation rejects empty list

    ## Test

    - Empty policy_ids list raises ValidationError

    ## Classes and Methods

    - PolicyIds.validate_policy_ids()
    """
    with pytest.raises(Exception):  # Pydantic ValidationError
        PolicyIds(policy_ids=[])


def test_policy_ids_00430():
    """
    # Summary

    Verify PolicyIds validation rejects empty strings

    ## Test

    - policy_ids with empty strings raises ValidationError

    ## Classes and Methods

    - PolicyIds.validate_policy_ids()
    """
    with pytest.raises(Exception):  # Pydantic ValidationError
        PolicyIds(policy_ids=["POLICY-123", ""])


def test_policy_ids_00440():
    """
    # Summary

    Verify PolicyIds with single policy ID

    ## Test

    - Works with a single policy ID

    ## Classes and Methods

    - PolicyIds.__init__()
    """
    with does_not_raise():
        policy_ids = PolicyIds(policy_ids=["POLICY-121110"])
        result = policy_ids.to_request_dict()
    assert result["policyIds"] == ["POLICY-121110"]


def test_policy_ids_00450():
    """
    # Summary

    Verify PolicyIds with multiple policy IDs

    ## Test

    - Works with many policy IDs

    ## Classes and Methods

    - PolicyIds.__init__()
    """
    ids = [f"POLICY-{i}" for i in range(1, 11)]
    with does_not_raise():
        policy_ids = PolicyIds(policy_ids=ids)
    assert len(policy_ids.policy_ids) == 10
