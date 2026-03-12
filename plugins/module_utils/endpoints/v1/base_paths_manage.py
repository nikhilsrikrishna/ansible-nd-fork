# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Allen Robel (@arobel) <arobel@cisco.com>

# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)
"""
Centralized base paths for ND Manage API endpoints.

/api/v1/manage

This module provides a single location to manage all API Manage base paths,
allowing easy modification when API paths change. All endpoint classes
should use these path builders for consistency.
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Final

from ansible_collections.cisco.nd.plugins.module_utils.endpoints.base_path import (
    ApiPath,
)


class BasePath:
    """
    # Summary

    API Endpoints for ND Manage

    ## Description

    Provides centralized endpoint definitions for all ND Manage API endpoints.
    This allows API path changes to be managed in a single location.

    ## Usage

    ```python
    from ansible_collections.cisco.nd.plugins.module_utils.endpoints.base_paths_manage import BasePath

    # Get a complete base path for ND Manage
    path = BasePath.nd_manage("inventory", "switches")
    # Returns: /api/v1/manage/inventory/switches

    # Leverage a convenience method
    path = BasePath.nd_manage_inventory("switches")
    # Returns: /api/v1/manage/inventory/switches
    ```

    ## Design Notes

    - All base paths are defined as class constants for easy modification
    - Helper methods compose paths from base constants
    - Use these methods in Pydantic endpoint models to ensure consistency
    - If ND Manage changes base API paths, only this class needs updating
    """

    API: Final = ApiPath.MANAGE.value

    @classmethod
    def nd_manage(cls, *segments: str) -> str:
        """
        # Summary

        Build ND manage API path.

        ## Parameters

        - segments: Path segments to append after /api/v1/manage

        ## Returns

        - Complete ND manage API path

        ## Example

        ```python
        path = BasePath.nd_manage("inventory", "switches")
        # Returns: /api/v1/manage/inventory/switches
        ```
        """
        if not segments:
            return cls.API
        return f"{cls.API}/{'/'.join(segments)}"

    @classmethod
    def nd_manage_inventory(cls, *segments: str) -> str:
        """
        # Summary

        Build ND manage inventory API path.

        ## Parameters

        - segments: Path segments to append after inventory (e.g., "switches")

        ## Returns

        - Complete ND manage inventory path

        ## Example

        ```python
        path = BasePath.nd_manage_inventory("switches")
        # Returns: /api/v1/manage/inventory/switches
        ```
        """
        return cls.nd_manage("inventory", *segments)

    @classmethod
    def nd_manage_fabrics(cls, *segments: str) -> str:
        """
        # Summary

        Build ND manage fabrics API path.

        ## Parameters

        - segments: Path segments to append after fabrics

        ## Returns

        - Complete ND manage fabrics path

        ## Example

        ```python
        path = BasePath.nd_manage_fabrics("my-fabric")
        # Returns: /api/v1/manage/fabrics/my-fabric

        path = BasePath.nd_manage_fabrics("my-fabric", "policies")
        # Returns: /api/v1/manage/fabrics/my-fabric/policies
        ```
        """
        return cls.nd_manage("fabrics", *segments)

    @classmethod
    def nd_manage_fabric_policies(cls, fabric_name: str, *segments: str) -> str:
        """
        # Summary

        Build ND manage fabric policies API path.

        ## Parameters

        - fabric_name: Name of the fabric (required)
        - segments: Additional path segments (e.g., policy_id)

        ## Returns

        - Complete ND manage fabric policies path

        ## Example

        ```python
        path = BasePath.nd_manage_fabric_policies("my-fabric")
        # Returns: /api/v1/manage/fabrics/my-fabric/policies

        path = BasePath.nd_manage_fabric_policies("my-fabric", "POLICY-123")
        # Returns: /api/v1/manage/fabrics/my-fabric/policies/POLICY-123
        ```
        """
        return cls.nd_manage_fabrics(fabric_name, "policies", *segments)

    @classmethod
    def nd_manage_fabric_policy_actions(cls, fabric_name: str, action: str) -> str:
        """
        # Summary

        Build ND manage fabric policyActions API path.

        ## Parameters

        - fabric_name: Name of the fabric (required)
        - action: The action to perform (markDelete, pushConfig, remove)

        ## Returns

        - Complete ND manage fabric policyActions path

        ## Example

        ```python
        path = BasePath.nd_manage_fabric_policy_actions("my-fabric", "markDelete")
        # Returns: /api/v1/manage/fabrics/my-fabric/policyActions/markDelete

        path = BasePath.nd_manage_fabric_policy_actions("my-fabric", "pushConfig")
        # Returns: /api/v1/manage/fabrics/my-fabric/policyActions/pushConfig
        ```
        """
        return cls.nd_manage_fabrics(fabric_name, "policyActions", action)

    @classmethod
    def nd_manage_config_templates(cls, *segments: str) -> str:
        """
        # Summary

        Build ND manage configTemplates API path.

        ## Parameters

        - segments: Path segments to append after configTemplates
                    (e.g., template_name, "parameters")

        ## Returns

        - Complete ND manage configTemplates path

        ## Example

        ```python
        path = BasePath.nd_manage_config_templates("switch_freeform")
        # Returns: /api/v1/manage/configTemplates/switch_freeform

        path = BasePath.nd_manage_config_templates("switch_freeform", "parameters")
        # Returns: /api/v1/manage/configTemplates/switch_freeform/parameters
        ```
        """
        return cls.nd_manage("configTemplates", *segments)
