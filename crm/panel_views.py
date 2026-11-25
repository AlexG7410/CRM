"""
Customer panel views — a separate, operational self-service panel where a
logged-in customer can view their orders, place new orders, track commissions,
invoices, payments, submit consultations and reviews, and edit their profile.

Authentication is separate from staff: a customer logs in at /panel/login/ with
a Django User that is linked (OneToOne) to a Customer record via Customer.user.
"""

from functools import wraps
from datetime import timedelta

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.utils import timezone

from .models import (
    Customer,
    Product,
    Consultation,
    SatisfactionReview,
    Order,
    OrderItem,
    Invoice,
    Payment,
    Commission,
    ActivityLog,
)
from .activity import log_activity


# ====================================================================
# HELPERS
# ====================================================================
def _get_customer(user):
    """Return the Customer linked to a user, or None."""
    if not user.is_authenticated:
        return None
    return getattr(user, "customer_profile", None)


def customer_required(view_func):
    """Decorator: user must be authenticated AND linked to a Customer."""
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        customer = _get_customer(request.user)
        if customer is None:
            return redirect("panel_login")
        request.customer = customer
        return view_func(request, *args, **kwargs)
    return _wrapped


def panel_render(request, template, context=None, active="panel_dashboard"):
    """Render a panel page with the customer injected into context."""
    ctx = {"active_nav": active, "customer": getattr(request, "customer", None)}
    if context:
        ctx.update(context)
    return render(request, template, ctx)


# ====================================================================
# AUTH
# ====================================================================
def panel_login(request):
    """Separate login for customers. Only users linked to a Customer may enter."""
    if request.user.is_authenticated and _get_customer(request.user):
        return redirect("panel_dashboard")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        if not username or not password:
            messages.error(request, "نام کاربری و گذرواژه را وارد کنید")
            return render(request, "panel/panel_login.html", {})
        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "نام کاربری یا گذرواژه اشتباه است")
            return render(request, "panel/panel_login.html", {})
        customer = _get_customer(user)
        if customer is None:
            # A staff user (or unlinked account) cannot use the customer panel
            messages.error(request, "این حساب به پنل مشتری دسترسی ندارد. لطفاً از حساب مشتری استفاده کنید.")
            return render(request, "panel/panel_login.html", {})
        if customer.status != Customer.StatusChoices.ACTIVE:
            messages.error(request, "حساب مشتری شما غیرفعال است. لطفاً با پشتیبانی تماس بگیرید.")
            return render(request, "panel/panel_login.html", {})
        auth_login(request, user)
        messages.success(request, f"خوش آمدید، {customer.name}")
        return redirect("panel_dashboard")
    return render(request, "panel/panel_login.html", {})


def panel_logout(request):
    if request.user.is_authenticated:
        auth_logout(request)
        messages.success(request, "از پنل مشتری خارج شدید")
    return redirect("panel_login")


# ====================================================================
# DASHBOARD
# ====================================================================
@customer_required
def panel_dashboard(request):
    customer = request.customer
    orders = list(customer.orders.order_by("-created_at"))
    commissions = list(customer.commissions.order_by("-created_at"))

    total_orders = len(orders)
    total_spent = sum(o.total for o in orders if o.total)
    total_commission = sum(c.commission_amount for c in commissions)
    pending_commission = sum(
        c.commission_amount for c in commissions if c.status == Commission.StatusChoices.PENDING
    )
    paid_commission = sum(
        c.commission_amount for c in commissions if c.status == Commission.StatusChoices.PAID
    )
    active_orders = sum(
        1 for o in orders if o.status not in ("confirmed_received", "cancelled")
    )
    recent_orders = orders[:5]

    context = {
        "total_orders": total_orders,
        "total_spent": total_spent,
        "total_commission": total_commission,
        "pending_commission": pending_commission,
        "paid_commission": paid_commission,
        "active_orders": active_orders,
        "recent_orders": recent_orders,
        "commission_rate": customer.commission_rate,
    }
    return panel_render(request, "panel/panel_dashboard.html", context, active="panel_dashboard")


# ====================================================================
# ORDERS
# ====================================================================
@customer_required
def panel_orders(request):
    customer = request.customer
    orders = list(customer.orders.order_by("-created_at"))
    context = {"orders": orders}
    return panel_render(request, "panel/panel_orders.html", context, active="panel_orders")


@customer_required
def panel_order_detail(request, pk):
    customer = request.customer
    order = get_object_or_404(Order, pk=pk, customer=customer)
    items = list(order.items.select_related("product"))
    context = {"order": order, "items": items}
    return panel_render(request, "panel/panel_order_detail.html", context, active="panel_orders")


@customer_required
def panel_order_new(request):
    """Customer places a new order: pick products + quantities, submit."""
    customer = request.customer
    if request.method == "POST":
        product_ids = request.POST.getlist("products")
        quantities = request.POST.getlist("quantities")
        notes = request.POST.get("notes", "").strip()
        order = Order.objects.create(customer=customer, notes=notes, status="pending")
        added = 0
        for pid, qty in zip(product_ids, quantities):
            try:
                product = Product.objects.get(id=pid, is_active=True)
                quantity = int(qty)
                if quantity > 0:
                    OrderItem.objects.create(
                        order=order, product=product, quantity=quantity, unit_price=product.price
                    )
                    added += 1
            except (Product.DoesNotExist, ValueError):
                continue
        if added:
            rate = float(customer.commission_rate) / 100
            order.commission_amount = int(order.subtotal * rate)
            order.save()
            messages.success(
                request,
                f"سفارش {order.number} با {added} قلم کالا و مبلغ {order.total:,} تومان ثبت شد",
            )
            log_activity(
                request, ActivityLog.ActionChoices.ORDER, "سفارشات (پنل مشتری)",
                f"ثبت سفارش {order.number} توسط «{customer.name}» - {added} قلم، {order.total:,} تومان",
                obj=order,
            )
            return redirect("panel_orders")
        else:
            order.delete()
            messages.error(request, "هیچ محصول معتبری انتخاب نشده بود")
            return redirect("panel_order_new")

    products_list = list(
        Product.objects.filter(is_active=True).select_related("brand").order_by("name")
    )
    context = {"products": products_list}
    return panel_render(request, "panel/panel_order_new.html", context, active="panel_order_new")


# ====================================================================
# COMMISSIONS
# ====================================================================
@customer_required
def panel_commissions(request):
    customer = request.customer
    commissions = list(customer.commissions.order_by("-created_at"))
    total = sum(c.commission_amount for c in commissions)
    pending = sum(c.commission_amount for c in commissions if c.status == Commission.StatusChoices.PENDING)
    approved = sum(c.commission_amount for c in commissions if c.status == Commission.StatusChoices.APPROVED)
    paid = sum(c.commission_amount for c in commissions if c.status == Commission.StatusChoices.PAID)
    context = {
        "commissions": commissions,
        "total": total,
        "pending": pending,
        "approved": approved,
        "paid": paid,
    }
    return panel_render(request, "panel/panel_commissions.html", context, active="panel_commissions")


# ====================================================================
# INVOICES & PAYMENTS
# ====================================================================
@customer_required
def panel_invoices(request):
    customer = request.customer
    invoices = list(customer.invoices.order_by("-created_at"))
    # Attach payments per invoice for display
    for inv in invoices:
        inv.payments_list = list(inv.payments.order_by("-created_at"))
    total_due = sum(
        inv.total for inv in invoices
        if inv.status not in ("paid", "draft")
    )
    total_paid = sum(
        p.amount for p in Payment.objects.filter(customer=customer, status="confirmed")
    )
    context = {
        "invoices": invoices,
        "total_due": total_due,
        "total_paid": total_paid,
    }
    return panel_render(request, "panel/panel_invoices.html", context, active="panel_invoices")


# ====================================================================
# CONSULTATION
# ====================================================================
@customer_required
def panel_consultation(request):
    customer = request.customer
    if request.method == "POST":
        wound_type = request.POST.get("wound_type", "other")
        question = request.POST.get("question", "").strip()
        if question:
            Consultation.objects.create(
                customer=customer,
                customer_name=customer.name,
                phone=customer.phone,
                wound_type=wound_type,
                question=question,
            )
            messages.success(request, "درخواست مشاوره شما ثبت شد. پاسخ به‌زودی در همین صفحه نمایش داده می‌شود.")
            log_activity(
                request, ActivityLog.ActionChoices.CREATE, "مشاوره (پنل مشتری)",
                f"ثبت درخواست مشاوره توسط «{customer.name}»",
            )
            return redirect("panel_consultation")
        messages.error(request, "متن سوال را وارد کنید")

    consultations = list(customer.consultations.order_by("-created_at"))
    wound_types = Consultation.WoundTypeChoices.choices
    context = {"consultations": consultations, "wound_types": wound_types}
    return panel_render(request, "panel/panel_consultation.html", context, active="panel_consultation")


# ====================================================================
# SATISFACTION REVIEW
# ====================================================================
@customer_required
def panel_review_add(request):
    customer = request.customer
    if request.method == "POST":
        rating = request.POST.get("rating", "5")
        comment = request.POST.get("comment", "").strip()
        product_quality = request.POST.get("product_quality", "5")
        service_quality = request.POST.get("service_quality", "5")
        delivery_speed = request.POST.get("delivery_speed", "5")
        try:
            SatisfactionReview.objects.create(
                customer=customer,
                rating=int(rating),
                comment=comment,
                product_quality=int(product_quality),
                service_quality=int(service_quality),
                delivery_speed=int(delivery_speed),
            )
            messages.success(request, "نظر شما با تشکر ثبت شد")
            log_activity(
                request, ActivityLog.ActionChoices.CREATE, "رضایت‌مندی (پنل مشتری)",
                f"ثبت نظر توسط «{customer.name}» - {rating} ستاره",
            )
            return redirect("panel_dashboard")
        except ValueError:
            messages.error(request, "اطلاعات نامعتبر است")
    context = {}
    return panel_render(request, "panel/panel_review_add.html", context, active="panel_review_add")


# ====================================================================
# PROFILE
# ====================================================================
@customer_required
def panel_profile(request):
    """Customer views and edits a limited set of their own fields."""
    customer = request.customer
    if request.method == "POST":
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        city = request.POST.get("city", "").strip()
        address = request.POST.get("address", "").strip()
        workplace = request.POST.get("workplace", "").strip()
        work_history = request.POST.get("work_history", "").strip()
        notes = request.POST.get("notes", "").strip()
        if not phone:
            messages.error(request, "شماره تماس الزامی است")
            return redirect("panel_profile")
        customer.phone = phone
        customer.email = email
        customer.city = city
        customer.address = address
        customer.workplace = workplace
        customer.work_history = work_history
        customer.notes = notes
        customer.save()
        messages.success(request, "اطلاعات شما به‌روزرسانی شد")
        log_activity(
            request, ActivityLog.ActionChoices.UPDATE, "پروفایل (پنل مشتری)",
            f"به‌روزرسانی پروفایل توسط «{customer.name}»",
            obj=customer,
        )
        return redirect("panel_profile")
    context = {"profile": customer}
    return panel_render(request, "panel/panel_profile.html", context, active="panel_profile")
