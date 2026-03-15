# Copyright (c) 2023-present Plane Software, Inc. and contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.

# Django imports
from django.db.models import Q

# Third party imports
from rest_framework import status
from rest_framework.response import Response

# Module imports
from plane.api.serializers import PageAPISerializer, PageAPICreateSerializer, PageAPIDetailSerializer
from plane.app.permissions import ProjectLitePermission, ProjectEntityPermission
from plane.db.models import Page
from .base import BaseAPIView


class PageListAPIEndpoint(BaseAPIView):
    """
    Provides a list of all pages in a project accessible to the authenticated user.
    """

    permission_classes = [ProjectEntityPermission]
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

    def post(self, request, slug, project_id):
        """Create a page in a project."""
        serializer = PageAPICreateSerializer(
            data=request.data,
            context={
                "project_id": project_id,
                "owned_by_id": request.user.id,
            },
        )

        if serializer.is_valid():
            if (
                request.data.get("external_id")
                and request.data.get("external_source")
                and Page.objects.filter(
                    project_pages__project_id=project_id,
                    workspace__slug=slug,
                    external_source=request.data.get("external_source"),
                    external_id=request.data.get("external_id"),
                    project_pages__deleted_at__isnull=True,
                ).exists()
            ):
                page = Page.objects.filter(
                    workspace__slug=slug,
                    project_pages__project_id=project_id,
                    external_source=request.data.get("external_source"),
                    external_id=request.data.get("external_id"),
                    project_pages__deleted_at__isnull=True,
                ).first()
                return Response(
                    {
                        "error": "Page with the same external id and external source already exists",
                        "id": str(page.id),
                    },
                    status=status.HTTP_409_CONFLICT,
                )

            serializer.save()
            return Response(PageAPISerializer(serializer.instance).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


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

        return Response(PageAPIDetailSerializer(page).data, status=status.HTTP_200_OK)
