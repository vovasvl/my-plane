# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db.models import Q

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.api.serializers import PageAPISerializer
from plane.app.permissions import ProjectLitePermission
from plane.db.models import Page, ProjectMember, ProjectPage
from .base import BaseAPIView


class PageListAPIEndpoint(BaseAPIView):
    """
    Provides a list of all pages in a project accessible to the authenticated user.
    """

    permission_classes = [ProjectLitePermission]
    use_read_replica = True

    def get_queryset(self):
        return (
            Page.objects.filter(
                workspace__slug=self.kwargs.get("slug"),
                projects__id=self.kwargs.get("project_id"),
                projects__project_projectmember__member=self.request.user,
                projects__project_projectmember__is_active=True,
                projects__archived_at__isnull=True,
                project_pages__deleted_at__isnull=True,
            )
            .filter(parent__isnull=True)
            .filter(Q(owned_by=self.request.user) | Q(access=0))
            .select_related("workspace", "owned_by")
            .order_by(self.request.GET.get("order_by", "-created_at"))
            .distinct()
        )

    def get(self, request, slug, project_id):
        """List all pages in a project.

        Returns a paginated list of pages accessible to the authenticated user.
        Supports filtering archived pages via `archived=true` query parameter.
        """
        queryset = self.get_queryset()

        archived = request.GET.get("archived", "false").lower() == "true"
        if archived:
            queryset = queryset.exclude(archived_at__isnull=True)
        else:
            queryset = queryset.filter(archived_at__isnull=True)

        return self.paginate(
            request=request,
            queryset=queryset,
            on_results=lambda pages: PageAPISerializer(pages, many=True).data,
            default_per_page=100,
        )


class PageDetailAPIEndpoint(BaseAPIView):
    """
    Retrieve a single page by its ID.
    """

    permission_classes = [ProjectLitePermission]
    use_read_replica = True

    def get(self, request, slug, project_id, pk):
        """Retrieve a page by its ID."""
        try:
            page = (
                Page.objects.filter(
                    pk=pk,
                    workspace__slug=slug,
                    projects__id=project_id,
                    projects__project_projectmember__member=request.user,
                    projects__project_projectmember__is_active=True,
                    project_pages__deleted_at__isnull=True,
                )
                .filter(Q(owned_by=request.user) | Q(access=0))
                .select_related("workspace", "owned_by")
                .distinct()
                .get()
            )
        except Page.DoesNotExist:
            return Response({"error": "Page not found"}, status=status.HTTP_404_NOT_FOUND)

        return Response(PageAPISerializer(page).data, status=status.HTTP_200_OK)
