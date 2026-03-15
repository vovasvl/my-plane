# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Third party imports
from rest_framework import serializers

# Module imports
from .base import BaseSerializer
from plane.db.models import Page, Project, ProjectPage


class PageAPISerializer(BaseSerializer):
    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "owned_by",
            "access",
            "color",
            "parent",
            "is_locked",
            "archived_at",
            "workspace",
            "created_at",
            "updated_at",
            "created_by",
            "updated_by",
            "view_props",
            "logo_props",
            "external_id",
            "external_source",
        ]
        read_only_fields = ["workspace", "owned_by"]


class PageAPICreateSerializer(BaseSerializer):
    description_html = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Page
        fields = [
            "id",
            "name",
            "access",
            "color",
            "parent",
            "view_props",
            "logo_props",
            "external_id",
            "external_source",
            "description_html",
        ]

    def create(self, validated_data):
        project_id = self.context["project_id"]
        owned_by_id = self.context["owned_by_id"]
        description_html = validated_data.pop("description_html", "<p></p>")

        project = Project.objects.get(pk=project_id)

        page = Page.objects.create(
            **validated_data,
            description_html=description_html,
            owned_by_id=owned_by_id,
            workspace_id=project.workspace_id,
        )

        ProjectPage.objects.create(
            workspace_id=page.workspace_id,
            project_id=project_id,
            page_id=page.id,
            created_by_id=page.created_by_id,
            updated_by_id=page.updated_by_id,
        )

        return page
