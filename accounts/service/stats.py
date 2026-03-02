"""
Dashboard Statistics Service
"""
import logging
from datetime import timedelta
from decimal import Decimal
from django.utils import timezone
from django.db.models import Q, Count
from django.contrib.auth import get_user_model

from employee.models import LeaveRequest, EmployeeContract, EmployeeSupervisor
from employee.utils.leave_logic import get_leave_balance
from projects.models import Activity, Milestone, ActivityReview, Project

logger = logging.getLogger(__name__)
User = get_user_model()



def _fmt_user(user) -> dict:
    return {
        "id": str(user.id),
        "name": user.get_full_name() or user.username,
        "email": user.email,
    }


def _activity_entry(act, extra: dict | None = None) -> dict:
    base = {
        "id": str(act.id),
        "name": act.name,
        "project": act.project.name,
        "project_id": str(act.project.id),
        "status": act.status,
        "priority": act.priority,
        "deadline": act.deadline,
        "is_complete": act.is_complete,
    }
    if extra:
        base.update(extra)
    return base


def _leave_entry(lr) -> dict:
    return {
        "id": str(lr.id),
        "employee": lr.user.get_full_name() or lr.user.username,
        "employee_id": str(lr.user.id),
        "type": lr.leave_type,
        "start_date": lr.start_date,
        "end_date": lr.end_date,
        "days": float(lr.days_requested),
        "status": lr.status,
        "created": lr.created_at,
    }


def _review_entry(r) -> dict:
    return {
        "id": str(r.id),
        "activity": r.activity.name,
        "activity_id": str(r.activity.id),
        "project": r.activity.project.name,
        "review_level": r.review_level,
        "status": r.status,
        "submitted_at": r.submitted_at,
        "created": r.created_at,
    }


def _leave_balance(user) -> dict:
    contract = EmployeeContract.objects.filter(
        user=user, is_current=True, is_expired=False
    ).first()

    if not contract:
        return {"has_contract": False, "balances": {}}

    leave_types = ["ANNUAL", "SICK", "MATERNITY", "PATERNITY", "COMPASSIONATE", "STUDY"]
    balances = {}
    for lt in leave_types:
        result = get_leave_balance(user, contract, lt)
        if isinstance(result, dict):
            balances[lt.lower()] = {
                k: float(v) if isinstance(v, Decimal) else v
                for k, v in result.items()
            }
        else:
            balances[lt.lower()] = float(result) if result is not None else None

    return {
        "has_contract": True,
        "contract_id": str(contract.id),
        "balances": balances,
    }


def _activity_counts(qs) -> dict:
    now = timezone.now()
    total       = qs.count()
    completed   = qs.filter(status="completed").count()
    in_progress = qs.filter(status="in_progress").count()
    not_started = qs.filter(status="not_started").count()
    overdue     = qs.filter(deadline__lt=now, status__in=["not_started", "in_progress"]).count()
    due_soon    = qs.filter(
        deadline__gte=now,
        deadline__lt=now + timedelta(days=7),
        status__in=["not_started", "in_progress"],
    ).count()
    return {
        "total": total,
        "completed": completed,
        "in_progress": in_progress,
        "not_started": not_started,
        "overdue": overdue,
        "due_soon": due_soon,
        "completion_rate": round((completed / total) * 100) if total else 0,
    }



def _personal_snapshot(user) -> dict:
    """
    Returns the logged-in user's own activities, leave balance, milestones
    and pending reviews regardless of their system role.
    This is embedded in every dashboard response under the key "personal".
    """
    now = timezone.now()

    my_acts = (
        Activity.objects
        .filter(responsible=user)
        .select_related("project")
    )

    act_counts = _activity_counts(my_acts)

    in_progress = list(my_acts.filter(status="in_progress").order_by("deadline")[:8])
    due_soon    = list(
        my_acts.filter(
            deadline__gte=now,
            deadline__lt=now + timedelta(days=7),
            status__in=["not_started", "in_progress"],
        ).order_by("deadline")[:8]
    )
    overdue = list(
        my_acts.filter(
            deadline__lt=now,
            status__in=["not_started", "in_progress"],
        ).order_by("deadline")[:5]
    )

    milestones = (
        Milestone.objects
        .filter(
            assigned_to=user,
            status__in=["not_started", "in_progress"],
            due_date__gte=now,
        )
        .select_related("activity", "activity__project")
        .order_by("due_date")[:8]
    )

    my_reviews = (
        ActivityReview.objects
        .filter(reviewer=user, status__in=["not_started", "started", "submitted"])
        .select_related("activity", "activity__project")
        .order_by("created_at")[:5]
    )

    recent_leaves = (
        LeaveRequest.objects
        .filter(user=user)
        .order_by("-created_at")[:5]
    )

    leave_bal = _leave_balance(user)

    return {
        "summary": {
            "activities_total": act_counts["total"],
            "activities_completed": act_counts["completed"],
            "activities_in_progress": act_counts["in_progress"],
            "activities_overdue": act_counts["overdue"],
            "completion_rate": act_counts["completion_rate"],
            "milestones_upcoming": milestones.count(),
            "pending_reviews": my_reviews.count(),
        },
        "leave": leave_bal,
        "recent_leave_requests": [_leave_entry(lr) for lr in recent_leaves],
        "activities": {
            **act_counts,
            "in_progress": [
                _activity_entry(a) for a in in_progress
            ],
            "due_soon": [
                _activity_entry(a, {
                    "days_remaining": (a.deadline - now).days if a.deadline else None,
                })
                for a in due_soon
            ],
            "overdue": [
                _activity_entry(a, {
                    "days_overdue": (now - a.deadline).days if a.deadline else None,
                })
                for a in overdue
            ],
        },
        "milestones": {
            "upcoming": [
                {
                    "id": str(m.id),
                    "title": m.title,
                    "activity": m.activity.name,
                    "activity_id": str(m.activity.id),
                    "project": m.activity.project.name,
                    "due_date": m.due_date,
                    "priority": m.priority,
                    "status": m.status,
                }
                for m in milestones
            ],
        },
        "reviews": {
            "pending_count": my_reviews.count(),
            "items": [_review_entry(r) for r in my_reviews],
        },
    }


# ─── admin ───────────────────────────────────────────────────────────────────

def _admin_stats(user) -> dict:
    now  = timezone.now()
    week = now - timedelta(days=7)

    # Pending leaves (org-wide)
    pending_leaves = (
        LeaveRequest.objects
        .filter(status="pending")
        .select_related("user")
        .order_by("created_at")[:8]
    )
    pending_leave_count = LeaveRequest.objects.filter(status="pending").count()

    # Activities (org-wide)
    all_acts = Activity.objects.select_related("project")
    act_counts = _activity_counts(all_acts)
    completed_this_week = all_acts.filter(
        completed_at__gte=week, status="completed"
    ).count()

    # Reviews needing admin action
    pending_reviews = (
        ActivityReview.objects
        .filter(review_level="admin", status__in=["not_started", "started", "submitted"])
        .select_related("activity", "activity__project", "reviewer")
        .order_by("created_at")[:8]
    )
    pending_review_count = ActivityReview.objects.filter(
        review_level="admin", status__in=["not_started", "started", "submitted"]
    ).count()

    # Contracts expiring in 30 days
    expiring = (
        EmployeeContract.objects
        .filter(
            is_current=True, is_expired=False,
            end_date__lte=now.date() + timedelta(days=30),
            end_date__gte=now.date(),
        )
        .select_related("user")
        .order_by("end_date")[:8]
    )
    expiring_count = expiring.count()

    # Projects summary
    project_counts = Project.objects.values("status").annotate(n=Count("id"))
    project_summary = {r["status"]: r["n"] for r in project_counts}
    total_projects = sum(project_summary.values())

    # Users
    total_users = User.objects.filter(is_active=True).count()

    return {
        "role": "admin",
        "summary": {
            "total_projects": total_projects,
            "project_by_status": project_summary,
            "total_users": total_users,
            "pending_leaves": pending_leave_count,
            "pending_reviews": pending_review_count,
            "contracts_expiring": expiring_count,
            "completed_this_week": completed_this_week,
        },
        "activities": act_counts,
        "leave_requests": {
            "pending_count": pending_leave_count,
            "items": [_leave_entry(lr) for lr in pending_leaves],
        },
        "reviews": {
            "pending_count": pending_review_count,
            "items": [_review_entry(r) for r in pending_reviews],
        },
        "contracts": {
            "expiring_count": expiring_count,
            "items": [
                {
                    "id": str(c.id),
                    "employee": c.user.get_full_name() or c.user.username,
                    "employee_id": str(c.user.id),
                    "end_date": c.end_date,
                    "days_remaining": (c.end_date - now.date()).days,
                }
                for c in expiring
            ],
        },
        # ← personal staff-level view for the logged-in admin
        "personal": _personal_snapshot(user),
    }


# ─── supervisor ──────────────────────────────────────────────────────────────

def _get_raci_role(user, act) -> str:
    if act.responsible_id == user.id:  return "Responsible"
    if act.accountable_id == user.id:  return "Accountable"
    return "Involved"


def _supervisor_stats(user) -> dict:
    now = timezone.now()

    # Team members
    team_ids = list(
        EmployeeSupervisor.objects
        .filter(supervisor=user, is_active=True)
        .values_list("employee_id", flat=True)
    )

    # Team pending leaves
    team_leaves = (
        LeaveRequest.objects
        .filter(user_id__in=team_ids, status="pending")
        .select_related("user")
        .order_by("created_at")[:8]
    )
    team_leave_count = LeaveRequest.objects.filter(
        user_id__in=team_ids, status="pending"
    ).count()

    # Activities where supervisor is involved (team-wide)
    my_acts = (
        Activity.objects
        .filter(
            Q(responsible=user) | Q(accountable=user) |
            Q(consulted=user)   | Q(informed=user)    |
            Q(activity_review__reviewer=user)
        )
        .select_related("project")
        .distinct()
    )

    act_counts = _activity_counts(my_acts)

    due_soon = list(
        my_acts.filter(
            deadline__gte=now,
            deadline__lt=now + timedelta(days=7),
            status__in=["not_started", "in_progress"],
        ).order_by("deadline")[:8]
    )

    overdue = list(
        my_acts.filter(
            deadline__lt=now,
            status__in=["not_started", "in_progress"],
        ).order_by("deadline")[:8]
    )

    # Reviews assigned to this supervisor
    pending_reviews = (
        ActivityReview.objects
        .filter(reviewer=user, status__in=["not_started", "started", "submitted"])
        .select_related("activity", "activity__project")
        .order_by("created_at")[:8]
    )
    pending_review_count = ActivityReview.objects.filter(
        reviewer=user, status__in=["not_started", "started", "submitted"]
    ).count()

    return {
        "role": "supervisor",
        "summary": {
            "team_size": len(team_ids),
            "pending_team_leaves": team_leave_count,
            "pending_reviews": pending_review_count,
            "activities_overdue": act_counts["overdue"],
            "activities_due_soon": act_counts["due_soon"],
            "activities_in_progress": act_counts["in_progress"],
        },
        "team": {
            "member_count": len(team_ids),
            "pending_leaves": {
                "count": team_leave_count,
                "items": [_leave_entry(lr) for lr in team_leaves],
            },
        },
        "activities": {
            **act_counts,
            "due_soon": [
                _activity_entry(a, {
                    "days_remaining": (a.deadline - now).days if a.deadline else None,
                    "my_role": _get_raci_role(user, a),
                })
                for a in due_soon
            ],
            "overdue": [
                _activity_entry(a, {
                    "days_overdue": (now - a.deadline).days if a.deadline else None,
                    "my_role": _get_raci_role(user, a),
                })
                for a in overdue
            ],
        },
        "reviews": {
            "pending_count": pending_review_count,
            "items": [_review_entry(r) for r in pending_reviews],
        },
        # ← personal staff-level view for the logged-in supervisor
        "personal": _personal_snapshot(user),
    }


def _staff_stats(user) -> dict:
    snapshot = _personal_snapshot(user)
    return {
        "role": "staff",
        **snapshot,
    }


class DashboardStatsService:

    @staticmethod
    def get_stats(user) -> dict:
        role = getattr(user, "role", "staff")
        if role == "admin" or user.is_superuser:
            return _admin_stats(user)
        elif role == "supervisor":
            return _supervisor_stats(user)
        else:
            return _staff_stats(user)