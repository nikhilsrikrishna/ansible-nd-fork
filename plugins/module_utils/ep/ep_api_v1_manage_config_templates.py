# -*- coding: utf-8 -*-

# Copyright: (c) 2026, Cisco Systems
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

"""
ND Manage Config Templates endpoint models.

This module contains endpoint definitions for configuration template
operations in the ND Manage API.

Endpoints covered:
- GET /configTemplates/{templateName}/parameters - Get template parameters only
"""

from __future__ import absolute_import, annotations, division, print_function

# pylint: disable=invalid-name
__metaclass__ = type
# pylint: enable=invalid-name

__author__ = "L Nikhil Sri Krishna"

from typing import Literal, Optional

from ansible_collections.cisco.nd.plugins.module_utils.enums import HttpVerbEnum
from ansible_collections.cisco.nd.plugins.module_utils.ep.base_paths_manage import BasePath
from ansible_collections.cisco.nd.plugins.module_utils.pydantic_compat import (
    BaseModel,
    ConfigDict,
    Field,
)


# Common Pydantic config
COMMON_CONFIG = ConfigDict(validate_assignment=True)


class EpApiV1ManageConfigTemplateParametersGet(BaseModel):
    """
    # Summary

    ND Manage Config Template Parameters GET Endpoint

    ## Description

    Retrieve only the parameters for a configuration template.
    Returns the same ``parameters`` array as the full template endpoint
    but without the template content.

    ## Path

    - /api/v1/manage/configTemplates/{templateName}/parameters

    ## Verb

    - GET

    ## Usage

    ```python
    request = EpApiV1ManageConfigTemplateParametersGet()
    request.template_name = "switch_freeform"
    path = request.path     # /api/v1/manage/configTemplates/switch_freeform/parameters
    verb = request.verb     # GET
    ```
    """

    model_config = COMMON_CONFIG

    class_name: Literal["EpApiV1ManageConfigTemplateParametersGet"] = Field(
        default="EpApiV1ManageConfigTemplateParametersGet",
        description="Class name for backward compatibility",
    )
    template_name: Optional[str] = Field(
        default=None,
        min_length=1,
        description="Configuration template name (e.g., switch_freeform, feature_enable)",
    )

    @property
    def path(self) -> str:
        """Build the endpoint path."""
        if self.template_name is None:
            raise ValueError("template_name must be set before accessing path")
        return BasePath.nd_manage_config_templates(self.template_name, "parameters")

    @property
    def verb(self) -> HttpVerbEnum:
        """Return the HTTP verb for this endpoint."""
        return HttpVerbEnum.GET
