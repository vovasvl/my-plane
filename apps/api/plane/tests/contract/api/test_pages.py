# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

import pytest
from rest_framework import status

from plane.db.models import Page, Project, ProjectMember, ProjectPage


@pytest.fixture
def project(db, workspace, create_user):
    """Create a test project with the user as an admin member."""
    project = Project.objects.create(
        name="Test Project",
        identifier="TP",
        workspace=workspace,
        created_by=create_user,
    )
    ProjectMember.objects.create(
        project=project,
        member=create_user,
        role=20,
        is_active=True,
    )
    return project


@pytest.mark.contract
class TestPageListCreateAPIEndpoint:
    """Test page list and create API endpoint."""

    def get_pages_url(self, workspace_slug, project_id):
        """Helper to get pages endpoint URL."""
        return f"/api/v1/workspaces/{workspace_slug}/projects/{project_id}/pages/"

    @pytest.mark.django_db
    def test_create_page_success(self, api_key_client, workspace, project):
        """Test successful page creation with description_html."""
        url = self.get_pages_url(workspace.slug, project.id)

        payload = {
            "name": "AI Review / 2026-W11",
            "description_html": "<h1>Weekly review</h1><p>Summary</p>",
            "access": 0,
        }

        response = api_key_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert Page.objects.count() == 1
        assert ProjectPage.objects.count() == 1

        created_page = Page.objects.first()
        assert created_page is not None
        assert created_page.name == payload["name"]
        assert created_page.description_html == payload["description_html"]

        project_link = ProjectPage.objects.first()
        assert project_link is not None
        assert project_link.project_id == project.id
        assert project_link.page_id == created_page.id

    @pytest.mark.django_db
    def test_create_page_duplicate_external_id(self, api_key_client, workspace, project, create_user):
        """Test creating page with duplicate external ID and source."""
        url = self.get_pages_url(workspace.slug, project.id)

        existing_page = Page.objects.create(
            workspace=workspace,
            owned_by=create_user,
            name="Existing Page",
            external_id="ext-123",
            external_source="perplexity",
        )
        ProjectPage.objects.create(
            workspace=workspace,
            project=project,
            page=existing_page,
            created_by=create_user,
            updated_by=create_user,
        )

        payload = {
            "name": "Second Page",
            "external_id": "ext-123",
            "external_source": "perplexity",
        }

        response = api_key_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "same external id" in response.data["error"]
        assert str(existing_page.id) == response.data["id"]
