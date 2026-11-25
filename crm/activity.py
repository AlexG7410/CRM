"""
Helper functions for logging user activities.
"""

from .models import ActivityLog


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip


def get_user_name(user):
    """Get display name for user."""
    if not user or not user.is_authenticated:
        return "کاربر ناشناس"
    if user.first_name and user.last_name:
        return f"{user.first_name} {user.last_name}"
    if user.first_name:
        return user.first_name
    return user.username


def log_activity(
    request,
    action,
    module,
    description,
    obj=None,
):
    """Log a user activity.

    Args:
        request: HttpRequest object
        action: One of ActivityLog.ActionChoices values
        module: Section/module name (e.g. "محصولات")
        description: Human-readable description
        obj: Optional model instance that was acted upon
    """
    user = getattr(request, "user", None)
    ActivityLog.objects.create(
        user=user if user and user.is_authenticated else None,
        user_name=get_user_name(user),
        action=action,
        module=module,
        description=description,
        object_id=str(obj.id) if obj and hasattr(obj, "id") else "",
        object_repr=str(obj)[:200] if obj else "",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500] if hasattr(request, "META") else "",
    )


def log_login(request, user):
    """Log a successful login."""
    ActivityLog.objects.create(
        user=user,
        user_name=get_user_name(user),
        action=ActivityLog.ActionChoices.LOGIN,
        module="احراز هویت",
        description=f"ورود به سیستم با نام کاربری {user.username}",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )


def log_logout(request, user):
    """Log a logout."""
    ActivityLog.objects.create(
        user=user,
        user_name=get_user_name(user),
        action=ActivityLog.ActionChoices.LOGOUT,
        module="احراز هویت",
        description=f"خروج از سیستم با نام کاربری {user.username}",
        ip_address=get_client_ip(request),
        user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
    )
