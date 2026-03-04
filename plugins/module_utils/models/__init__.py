# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
Pydantic models for ND API request and response bodies.

This package contains data models for various ND API operations,
providing type safety, validation, and serialization.

## Submodules

- policy_create: Models for creating policies
- policy_update: Models for updating policies
- policy_actions: Models for policy bulk actions (markDelete, pushConfig, remove)
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "Cisco Systems"

from ansible_collections.cisco.nd.plugins.module_utils.models.policy import (
    PolicyCreate,
    PolicyCreateBulk,
    PolicyEntityType,
    PolicyIds,
    PolicyUpdate,
)

__all__ = [
    "PolicyCreate",
    "PolicyCreateBulk",
    "PolicyEntityType",
    "PolicyUpdate",
    "PolicyIds",
]
