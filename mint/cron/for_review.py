from django.utils import timezone
from django.db import transaction
from mint.models import Project, ProjectReview, ProjectReviewStatus
import logging

logger = logging.getLogger(__name__)

def move_completed_projects_to_review():
    """
    Move all completed projects to review status if they don't already have a review.
    Runs daily at 8 AM.
    """
    try:
        # Find all completed projects that don't have a review yet
        completed_projects = Project.objects.filter(
            status='completed'
        ).exclude(
            project_review__isnull=False  
        )
        
        created_count = 0
        
        for project in completed_projects:
            try:
                with transaction.atomic():
                    # Create a new ProjectReview for this completed project
                    ProjectReview.objects.create(
                        project=project,
                        status=ProjectReviewStatus.PENDING,
                        created_by=project.owner,
                        submitted_at=timezone.now()
                    )
                    created_count += 1
                    
                    logger.info(f"Created review for project: {project.name} (ID: {project.id})")
                    
            except Exception as e:
                logger.error(f"Failed to create review for project {project.id}: {str(e)}")
                continue
        
        logger.info(f"Successfully moved {created_count} completed projects to review")
        
    except Exception as e:
        logger.error(f"Error in move_completed_projects_to_review cronjob: {str(e)}")