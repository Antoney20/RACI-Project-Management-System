from django.db.models import Q, Prefetch
from django.utils import timezone

from mint.models import Sprint
from projects.models import Activity, Milestone, Project



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
            "assigned_to": milestone.assigned_to.id if milestone.assigned_to else None,
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
            "responsible": activity.responsible.id if activity.responsible else None,
            "accountable": activity.accountable.id if activity.accountable else None,
            "completion_rate": completion_rate,
            "is_complete": activity.is_complete,
            "milestones": [
                SprintDetailsService._milestone_payload(m)
                for m in milestones
            ]
        }

    @staticmethod
    def _project_payload(project):
        activities = project.activities.all()

        total = activities.count()
        completed = activities.filter(is_complete=True).count()

        progress = 0
        if total > 0:
            progress = round((completed / total) * 100, 2)

        return {
            "id": str(project.id),
            "name": project.name,
            "status": project.status,
            "priority": project.priority,
            "progress": progress,
            "created_by": project.created_by.id if project.created_by else None,
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
                queryset=Project.objects.prefetch_related(
                    Prefetch(
                        "activities",
                        queryset=Activity.objects.prefetch_related("milestones")
                    )
                )
            )
        ).get(id=sprint_id)

        # 🔐 ACCESS CONTROL
        if user.is_admin() or user.is_office_admin():
            pass
        else:
            if not SprintDetailsService._is_user_involved(user, sprint):
                return None

        projects = sprint.projects.all()

        total_projects = projects.count()
        total_activities = Activity.objects.filter(
            project__sprint=sprint
        ).count()

        completed_activities = Activity.objects.filter(
            project__sprint=sprint,
            is_complete=True
        ).count()

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
                SprintDetailsService._project_payload(p)
                for p in projects
            ]
        }