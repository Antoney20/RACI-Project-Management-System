from typing import Any
import datetime
from django.contrib.auth import get_user_model
from django.db.models import Q, Prefetch, QuerySet
from rest_framework import status
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet
from rest_framework.permissions import IsAuthenticated

from mint.models import Sprint
from projects.models import (
    Project, Activity, Milestone,
    ActivityComment, ActivityDocument, ActivityReview,
)
from projects.serializers import UserMinimalSerializer

User = get_user_model()


def _user(u) -> dict | None:
    return UserMinimalSerializer(u).data if u else None

def _users(qs) -> list:
    return UserMinimalSerializer(qs, many=True).data

def _td(delta) -> str | None:
    return str(delta) if delta else None


def _supervisor_activity_ids(user) -> QuerySet:
    """
    Return a queryset of Activity PKs the supervisor is allowed to see
    """
    return Activity.objects.filter(
        Q(responsible=user) |
        Q(accountable=user) |
        Q(consulted=user) |
        Q(informed=user) |
        Q(activity_review__reviewer=user)
    ).values_list("id", flat=True).distinct()


def _activity_qs(activity_filter: Q | None = None):
    """
    Build a prefetched Activity queryset.
    Pass a Q filter to scope which activities are fetched.
    """
    qs = Activity.objects
    if activity_filter is not None:
        qs = qs.filter(activity_filter)
    return (
        qs
        .select_related("responsible", "accountable")
        .prefetch_related(
            "consulted",
            "informed",
            Prefetch(
                "comments",
                queryset=ActivityComment.objects.select_related("user").order_by("created_at"),
            ),
            Prefetch(
                "documents",
                queryset=ActivityDocument.objects.select_related("uploaded_by"),
            ),
            Prefetch(
                "milestones",
                queryset=Milestone.objects.select_related("assigned_to"),
            ),
            Prefetch(
                "activity_review",
                queryset=ActivityReview.objects.select_related("reviewer").order_by("created_at"),
            ),
        )
        .order_by("order")
    )



def _shape_review(r: "ActivityReview", activity: "Activity") -> dict:
    submitted_to_decided = _td(
        (r.decided_at - r.submitted_at) if r.decided_at and r.submitted_at else None
    )
    created_to_submitted = _td(
        (r.submitted_at - activity.created_at) if r.submitted_at and activity.created_at else None
    )
    total = _td(
        (r.decided_at - activity.created_at) if r.decided_at and activity.created_at else None
    )
    return {
        "id": str(r.id),
        "review_level": r.get_review_level_display(),
        "status": r.get_status_display(),
        "decision": r.decision,
        "reviewer": _user(r.reviewer),
        "is_complete": r.is_complete,
        "submitted_at": r.submitted_at,
        "decided_at": r.decided_at,
        "turnaround": {
            "created_to_submitted": created_to_submitted,
            "submitted_to_decided": submitted_to_decided,
            "total": total,
        },
    }


def _shape_milestone(m: "Milestone") -> dict:
    return {
        "id": str(m.id),
        "title": m.title,
        "description": m.description,
        "assigned_to": _user(m.assigned_to),
        "status": m.get_status_display(),
        "priority": m.get_priority_display(),
        "due_date": m.due_date,
        "is_completed": m.is_completed,
        "completed_at": m.completed_at,
        "comments": [],  
    }


def _shape_activity(a: "Activity") -> dict:
    reviews = [_shape_review(r, a) for r in a.activity_review.all()]

    review_summary: dict[str, dict] = {}
    for r in a.activity_review.all():
        lvl = r.get_review_level_display()
        review_summary[lvl] = {
            "status": r.get_status_display(),
            "decision": r.decision,
            "reviewer": _user(r.reviewer),
            "decided_at": r.decided_at,
        }

    return {
        "id": str(a.id),
        "name": a.name,
        "description": a.description,
        "type": a.get_type_display(),
        "status": a.get_status_display(),
        "priority": a.get_priority_display(),
        "deadline": a.deadline,
        "is_complete": a.is_complete,
        "completed_at": a.completed_at,
        "order": a.order,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
        "responsible": _user(a.responsible),
        "accountable": _user(a.accountable),
        "consulted": _users(a.consulted.all()),
        "informed": _users(a.informed.all()),
        "milestones": [_shape_milestone(m) for m in a.milestones.all()],
        "comments": [
            {
                "id": str(c.id),
                "user": _user(c.user),
                "content": c.content,
                "created_at": c.created_at,
            }
            for c in a.comments.all()
        ],
        "documents": [
            {
                "id": str(d.id),
                "title": d.title,
                "description": d.description,
                "file_url": d.file.url if d.file else None,
                "external_url": d.external_url,
                "uploaded_by": _user(d.uploaded_by),
                "created_at": d.created_at,
            }
            for d in a.documents.all()
        ],
        "reviews": reviews,
        "review_summary": review_summary,
    }


def _shape_project(p: "Project", activities: list[dict]) -> dict:
    total       = len(activities)
    completed   = sum(1 for a in activities if a["is_complete"])
    in_progress = sum(1 for a in activities if a["status"] == "In Progress")
    not_started = sum(1 for a in activities if a["status"] == "Not Started")

    return {
        "id": str(p.id),
        "name": p.name,
        "description": p.description,
        "deliverables": p.deliverables,
        "status": p.status,
        "priority": p.priority,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "duration_days": p.duration_days,
        "project_link": p.project_link,
        "created_at": p.created_at,
        "sprint": {"id": p.sprint_id, "name": p.sprint.name} if p.sprint else None,
        "activity_stats": {
            "total": total,
            "completed": completed,
            "in_progress": in_progress,
            "not_started": not_started,
        },
        "activities": activities,
    }


def _shape_sprint(s: "Sprint", projects: list[dict]) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "description": s.description,
        "start_date": s.start_date,
        "end_date": s.end_date,
        "is_active": s.is_active,
        "department": s.department,
        "duration_template": s.duration_template,
        "sprint_goals": s.sprint_goals,
        "expected_deliverables": s.expected_deliverables,
        "created_by": _user(s.created_by),
        "project_count": len(projects),
        "projects": projects,
    }



def _build_user_workload(allowed_activity_ids: QuerySet) -> list[dict]:
    activity_qs = (
        Activity.objects
        .filter(id__in=allowed_activity_ids)
        .select_related("responsible", "accountable", "project")
    )

    workload: dict[str, dict] = {}

    def _ensure(user_obj) -> dict:
        uid = str(user_obj.id)
        if uid not in workload:
            workload[uid] = {
                "user": _user(user_obj),
                "responsible_for": [],
                "accountable_for": [],
                "stats": {
                    "total_responsible": 0, "completed_responsible": 0,
                    "total_accountable": 0, "completed_accountable": 0,
                },
            }
        return workload[uid]

    for a in activity_qs:
        entry = {
            "activity_id": str(a.id),
            "activity_name": a.name,
            "project": a.project.name,
            "status": a.get_status_display(),
            "priority": a.get_priority_display(),
            "deadline": a.deadline,
            "is_complete": a.is_complete,
        }
        if a.responsible:
            bucket = _ensure(a.responsible)
            bucket["responsible_for"].append(entry)
            bucket["stats"]["total_responsible"] += 1
            if a.is_complete:
                bucket["stats"]["completed_responsible"] += 1
        if a.accountable:
            bucket = _ensure(a.accountable)
            bucket["accountable_for"].append(entry)
            bucket["stats"]["total_accountable"] += 1
            if a.is_complete:
                bucket["stats"]["completed_accountable"] += 1

    return list(workload.values())



class ActivityReportService:

    @staticmethod
    def compile_report(user) -> dict:
        is_admin = user.is_superuser or user.role == "admin"

        if is_admin:
            allowed_activity_ids = (
                Activity.objects.values_list("id", flat=True)
            )
            project_qs = (
                Project.objects
                .select_related("sprint", "sprint__created_by")
                .order_by("-created_at")
            )
            def activity_q_for_project(project_id):
                return Q(project_id=project_id)
        else:
            allowed_activity_ids = _supervisor_activity_ids(user)
            project_qs = (
                Project.objects
                .filter(activities__id__in=allowed_activity_ids)
                .select_related("sprint", "sprint__created_by")
                .distinct()
                .order_by("-created_at")
            )

            def activity_q_for_project(project_id):
                return Q(project_id=project_id, id__in=allowed_activity_ids)

        projects_by_id: dict[str, dict] = {}
        for p in project_qs:
            scoped_activities = list(
                _activity_qs(activity_q_for_project(p.id))
            )
            shaped_activities = [_shape_activity(a) for a in scoped_activities]
            projects_by_id[str(p.id)] = _shape_project(p, shaped_activities)

        sprint_map: dict[int, dict] = {}
        no_sprint_projects: list[dict] = []

        for p in project_qs:
            shaped = projects_by_id[str(p.id)]
            if p.sprint_id:
                if p.sprint_id not in sprint_map:
                    sprint_map[p.sprint_id] = {"sprint_obj": p.sprint, "projects": []}
                sprint_map[p.sprint_id]["projects"].append(shaped)
            else:
                no_sprint_projects.append(shaped)

        sprints = [
            _shape_sprint(v["sprint_obj"], v["projects"])
            for v in sprint_map.values()
        ]

        users = _users(User.objects.all()) if is_admin else []

        workload = _build_user_workload(allowed_activity_ids)

        all_activities: list[dict] = [
            a for p in projects_by_id.values() for a in p["activities"]
        ]
        today = datetime.date.today()
        stats = {
            "total_sprints": len(sprints),
            "total_projects": len(projects_by_id),
            "total_activities": len(all_activities),
            "completed_activities": sum(1 for a in all_activities if a["is_complete"]),
            "in_progress_activities": sum(1 for a in all_activities if a["status"] == "In Progress"),
            "overdue_activities": sum(
                1 for a in all_activities
                if a["deadline"] and not a["is_complete"]
                and a["deadline"].date() < today
            ),
        }

        return {
            "stats": stats,
            "users": users,
            "user_workload": workload,
            "sprints": sprints,
            "no_sprint_projects": no_sprint_projects,
        }



class ActivityReportsViewSet(ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        user = request.user

        if not (user.is_superuser or getattr(user, "role", None) in ("admin", "supervisor")):
            return Response(
                {"error": "You do not have permission to view reports."},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            return Response(
                ActivityReportService.compile_report(user),
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": f"Failed to compile report: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )