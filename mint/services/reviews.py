# from django.utils import timezone
# from django.db import transaction
# from mint.models import Project, ProjectReview, ProjectReviewStatus
# import logging

# logger = logging.getLogger(__name__)


# def move_project_to_review(project):
#     """
#     Create a ProjectReview for ONE completed project if it doesn't exist.
#     Safe to call multiple times (idempotent).
#     """
#     if project.status != "completed":
#         return False

#     if hasattr(project, "project_review"):
#         return False

#     try:
#         with transaction.atomic():
#             ProjectReview.objects.create(
#                 project=project,
#                 status=ProjectReviewStatus.PENDING,
#                 created_by=project.owner,
#                 submitted_at=timezone.now()
#             )

#             logger.info(
#                 f"Created review for project: {project.name} (ID: {project.id})"
#             )
#             return True

#     except Exception as e:
#         logger.error(
#             f"Failed to create review for project {project.id}: {str(e)}"
#         )
#         return False