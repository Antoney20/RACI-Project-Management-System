import uuid
from typing import Dict, List, Any, Optional
from django.contrib.auth import get_user_model
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django.utils import timezone
from rest_framework.response import Response
from rest_framework import status

from mint.models import Sprint  
from projects.models import (
    Project, Activity,  Milestone,
    ActivityComment, ActivityDocument,
    SupervisorReview
)
from projects.serializers import UserMinimalSerializer  

User = get_user_model()


class ActivityReportService:
    @staticmethod
    def get_all_users() -> List[Dict[str, Any]]:
        """Fetch all users in minimal format."""
        users = User.objects.all()
        return UserMinimalSerializer(users, many=True).data

    @staticmethod
    def get_projects_for_user(user: User) -> QuerySet[Project]:
        """Get projects based on user role and involvement."""
        if user.is_superuser or user.role == 'admin':  # Assuming role field or is_superuser
            return Project.objects.all()
        elif user.role == 'supervisor':
            # Supervisors see projects where they are involved (e.g., accountable, consulted, etc.)
            # or activities where they are reviewer
            activity_qs = Activity.objects.filter(
                Q(accountable=user) |
                Q(consulted=user) |
                Q(informed=user) |
                Q(supervisor_reviews__reviewer=user)
            ).distinct()
            return Project.objects.filter(activities__in=activity_qs).distinct()
        else:
            # Regular users see nothing
            return Project.objects.none()

    @staticmethod
    def get_activities_for_project(project: Project) -> List[Dict[str, Any]]:
        """Get detailed activities for a project with roles, dates, status, etc."""
        activities = Activity.objects.filter(project=project).order_by('order')
        activity_data = []
        for activity in activities:
            data = {
                'id': str(activity.id),
                'name': activity.name,
                'description': activity.description,
                'type': activity.get_type_display(),
                'status': activity.get_status_display(),
                'priority': activity.get_priority_display(),
                'deadline': activity.deadline,
                'is_complete': activity.is_complete,
                'completed_at': activity.completed_at,
                'responsible': UserMinimalSerializer(activity.responsible).data if activity.responsible else None,
                'accountable': UserMinimalSerializer(activity.accountable).data if activity.accountable else None,
                'consulted': UserMinimalSerializer(activity.consulted.all(), many=True).data,
                'informed': UserMinimalSerializer(activity.informed.all(), many=True).data,
                'comments': ActivityReportService.get_comments_for_activity(activity),
                'documents': ActivityReportService.get_documents_for_activity(activity),
                'milestones': ActivityReportService.get_milestones_for_activity(activity),
                'supervisor_reviews': ActivityReportService.get_supervisor_reviews_for_activity(activity),
                'created_at': activity.created_at,
                'updated_at': activity.updated_at,
            }
            activity_data.append(data)
        return activity_data

    @staticmethod
    def get_comments_for_activity(activity: Activity) -> List[Dict[str, Any]]:
        """Get comments for an activity."""
        comments = ActivityComment.objects.filter(activity=activity)
        return [{
            'id': str(c.id),
            'user': UserMinimalSerializer(c.user).data,
            'content': c.content,
            'created_at': c.created_at,
        } for c in comments]

    @staticmethod
    def get_documents_for_activity(activity: Activity) -> List[Dict[str, Any]]:
        """Get documents/links for an activity."""
        docs = ActivityDocument.objects.filter(activity=activity)
        return [{
            'id': str(d.id),
            'title': d.title,
            'description': d.description,
            'file_url': d.file.url if d.file else None,
            'external_url': d.external_url,
            'uploaded_by': UserMinimalSerializer(d.uploaded_by).data,
            'created_at': d.created_at,
        } for d in docs]

    @staticmethod
    def get_milestones_for_activity(activity: Activity) -> List[Dict[str, Any]]:
        """Get milestones with comments and details."""
        milestones = Milestone.objects.filter(activity=activity)
        milestone_data = []
        for m in milestones:
            data = {
                'id': str(m.id),
                'title': m.title,
                'description': m.description,
                'assigned_to': UserMinimalSerializer(m.assigned_to).data if m.assigned_to else None,
                'status': m.get_status_display(),
                'priority': m.get_priority_display(),
                'due_date': m.due_date,
                'is_completed': m.is_completed,
                'completed_at': m.completed_at,
                'comments': [{
                    'id': str(c.id),
                    'user': UserMinimalSerializer(c.user).data,
                    'content': c.content,
                    'created_at': c.created_at,
                } for c in m.comments.all()],
            }
            milestone_data.append(data)
        return milestone_data

    @staticmethod
    def get_supervisor_reviews_for_activity(activity: Activity) -> List[Dict[str, Any]]:
        """Get supervisor reviews with turnaround times and details."""
        reviews = SupervisorReview.objects.filter(activity=activity)
        review_data = []
        for r in reviews:
            created_to_start = (r.started_at - activity.created_at) if r.started_at and activity.created_at else None
            start_to_approved = (r.supervisor_approved_at - r.started_at) if r.supervisor_approved_at and r.started_at else None
            approved_to_completed = (r.completed_at - r.supervisor_approved_at) if r.completed_at and r.supervisor_approved_at else None
            total_turnaround = (r.completed_at - activity.created_at) if r.completed_at and activity.created_at else None

            completed_on_time = False
            if r.completed_at and activity.deadline:
                completed_on_time = r.completed_at <= activity.deadline

            data = {
                'id': str(r.id),
                'review_level': r.get_review_level_display(),
                'status': r.get_status_display(),
                'reviewer': UserMinimalSerializer(r.reviewer).data if r.reviewer else None,
                'is_supervisor_approved': r.is_supervisor_approved,
                'supervisor_approved_at': r.supervisor_approved_at,
                'move_to_admin': r.move_to_admin,
                'is_admin_approved': r.is_admin_approved,
                'admin_approved_at': r.admin_approved_at,
                'notes': r.notes,
                'started_at': r.started_at,
                'completed_at': r.completed_at,
                'is_complete': r.is_complete,
                'completed_on_time': completed_on_time,
                'turnaround_times': {
                    'created_to_start': str(created_to_start) if created_to_start else None,
                    'start_to_approved': str(start_to_approved) if start_to_approved else None,
                    'approved_to_completed': str(approved_to_completed) if approved_to_completed else None,
                    'total': str(total_turnaround) if total_turnaround else None,
                },
            }
            review_data.append(data)
        return review_data

    @staticmethod
    def compile_report(user: User) -> Dict[str, Any]:
        """Compile full report data."""
        try:
            users = ActivityReportService.get_all_users() if user.role in ['admin', 'supervisor'] else []
            projects = ActivityReportService.get_projects_for_user(user)
            project_data = []
            for project in projects:
                data = {
                    'id': str(project.id),
                    'name': project.name,
                    'description': project.description,
                    'deliverables': project.deliverables,
                    'status': project.status,
                    'priority': project.priority,
                    'start_date': project.start_date,
                    'end_date': project.end_date,
                    'duration_days': project.duration_days,
                    'project_link': project.project_link,
                    'activities': ActivityReportService.get_activities_for_project(project),
                }
                project_data.append(data)
            return {
                'users': users,
                'projects': project_data,
            }
        except Exception as e:
            raise ValueError(f"Failed to compile report: {str(e)}")