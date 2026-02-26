from django.db.models import Q, Prefetch
from django.utils import timezone

from mint.models import Sprint
from projects.models import Activity, Milestone, Project
from projects.serializers import UserMinimalSerializer



class SprintDetailsService:

    @staticmethod
    def _is_user_involved(user, sprint: Sprint) -> bool:
        """
        Check if user is involved in this sprint via:
        - Project creator
        - Responsible / Accountable
        - Consulted / Informed
        - Milestone assignee
        """

        return Activity.objects.filter(
            project__sprint=sprint
        ).filter(
            Q(responsible=user) |
            Q(accountable=user) |
            Q(consulted=user) |
            Q(informed=user)
        ).exists() or Project.objects.filter(
            sprint=sprint,
            created_by=user
        ).exists() or Milestone.objects.filter(
            activity__project__sprint=sprint,
            assigned_to=user
        ).exists()

    @staticmethod
    def _is_user_involved_in_activity(user, activity) -> bool:
        """
        Check if user is involved in this activity via:
        - Responsible / Accountable / Consulted / Informed
        - Project creator
        - Milestone assignee
        """
        return (
            activity.responsible == user or
            activity.accountable == user or
            activity.consulted == user or
            activity.informed == user or
            activity.project.created_by == user or
            activity.milestones.filter(assigned_to=user).exists()
        )
        
    @staticmethod
    def _user_payload(user):
        if not user:
            return None
        return UserMinimalSerializer(user).data

    @staticmethod
    def _milestone_payload(milestone):
        now = timezone.now()

        completed_on_time = False
        if milestone.is_completed and milestone.completed_at and milestone.due_date:
            completed_on_time = milestone.completed_at <= milestone.due_date

        return {
            "id": str(milestone.id),
            "title": milestone.title,
            "status": milestone.status,
            "priority": milestone.priority,
            "due_date": milestone.due_date,
            "assigned_to": SprintDetailsService._user_payload(
                milestone.assigned_to
            ),
            "is_completed": milestone.is_completed,
            "completed_on_time": completed_on_time,
        }

    @staticmethod
    def _activity_payload(activity):
        milestones = activity.milestones.all()

        total_milestones = milestones.count()
        completed_milestones = milestones.filter(is_completed=True).count()

        completion_rate = 0
        if total_milestones > 0:
            completion_rate = round((completed_milestones / total_milestones) * 100, 2)

        return {
            "id": str(activity.id),
            "name": activity.name,
            "status": activity.status,
            "priority": activity.priority,
            "deadline": activity.deadline,
            "responsible": SprintDetailsService._user_payload(activity.responsible),
            "accountable": SprintDetailsService._user_payload(activity.accountable),
            "completion_rate": completion_rate,
            "is_complete": activity.is_complete,
            "milestones": [
                SprintDetailsService._milestone_payload(m)
                for m in milestones
            ]
        }

    @staticmethod
    def _project_payload(project, user=None, is_admin=False):
        """
        Project payload with optional user-based activity filtering.
        If user is provided and not admin, only return activities the user is involved in.
        """
        activities = project.activities.all()

        # Filter activities if user is not admin
        if user and not is_admin:
            activities = [
                a for a in activities
                if SprintDetailsService._is_user_involved_in_activity(user, a)
            ]
        else:
            activities = list(activities)

        total = len(activities)
        completed = sum(1 for a in activities if a.is_complete)

        progress = 0
        if total > 0:
            progress = round((completed / total) * 100, 2)

        return {
            "id": str(project.id),
            "name": project.name,
            "status": project.status,
            "priority": project.priority,
            "progress": progress,
            "created_by": SprintDetailsService._user_payload(project.created_by),
            "activities": [
                SprintDetailsService._activity_payload(a)
                for a in activities
            ]
        }

    @staticmethod
    def get_sprint_details(user, sprint_id):
        sprint = Sprint.objects.prefetch_related(
            Prefetch(
                "projects",
                queryset=Project.objects.select_related("created_by").prefetch_related(
                    Prefetch(
                        "activities",
                        queryset=Activity.objects.select_related(
                            "responsible", "accountable"
                        ).prefetch_related(
                            Prefetch(
                                "milestones",
                                queryset=Milestone.objects.select_related("assigned_to")
                            )
                        )
                    )
                )
            )
        ).get(id=sprint_id)

        is_admin = user.is_admin() or user.is_office_admin()

        # Check permission: user must be involved or be admin
        if not is_admin:
            if not SprintDetailsService._is_user_involved(user, sprint):
                return None

        projects = sprint.projects.all()

        # For non-admin users, filter activities and recalculate progress
        if is_admin:
            # Admin sees everything
            total_projects = projects.count()
            total_activities = Activity.objects.filter(
                project__sprint=sprint
            ).count()
            completed_activities = Activity.objects.filter(
                project__sprint=sprint,
                is_complete=True
            ).count()
        else:
            # Non-admin sees only activities they're involved in
            all_activities = Activity.objects.filter(
                project__sprint=sprint
            ).select_related("project").prefetch_related("milestones")
            
            user_activities = [
                a for a in all_activities
                if SprintDetailsService._is_user_involved_in_activity(user, a)
            ]
            
            total_projects = projects.count()
            total_activities = len(user_activities)
            completed_activities = sum(1 for a in user_activities if a.is_complete)

        overall_progress = 0
        if total_activities > 0:
            overall_progress = round(
                (completed_activities / total_activities) * 100,
                2
            )

        return {
            "id": str(sprint.id),
            "name": sprint.name,
            "start_date": sprint.start_date,
            "end_date": sprint.end_date,
            "total_projects": total_projects,
            "total_activities": total_activities,
            "completed_activities": completed_activities,
            "overall_progress": overall_progress,
            "projects": [
                SprintDetailsService._project_payload(p, user=user, is_admin=is_admin)
                for p in projects
            ]
        }