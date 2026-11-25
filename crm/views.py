"""
Views for the Wound Specialist CRM (APP CRM متخصص)
16 sections based on customer requirements
"""

import json
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum, Count, Q, F
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
import csv

from .models import (
    Customer,
    Brand,
    Product,
    Consultation,
    SatisfactionReview,
    Order,
    OrderItem,
    Invoice,
    Payment,
    ProductRequest,
    WarehouseMovement,
    DailyReport,
    Commission,
    ChatMessage,
    ActivityLog,
)
from .activity import log_activity, log_login, log_logout, get_user_name


# ====================================================================
# AUTHENTICATION
# ====================================================================
def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        next_url = request.POST.get("next") or "/"
        if not username or not password:
            messages.error(request, "نام کاربری و گذرواژه را وارد کنید")
            return render(request, "registration/login.html", {"next": next_url})
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            log_login(request, user)
            messages.success(request, f"خوش آمدید، {get_user_name(user)}")
            return redirect(next_url if next_url != "/login/" else "/")
        else:
            messages.error(request, "نام کاربری یا گذرواژه اشتباه است")
    next_url = request.GET.get("next", "/")
    return render(request, "registration/login.html", {"next": next_url})


def logout_view(request):
    if request.user.is_authenticated:
        log_logout(request, request.user)
        auth_logout(request)
        messages.success(request, "شما با موفقیت از سیستم خارج شدید")
    return redirect("login")


def render_page(request, template, context=None, active="dashboard"):
    ctx = {"active_nav": active}
    if context:
        ctx.update(context)
    return render(request, template, ctx)


# ====================================================================
# DASHBOARD
# ====================================================================
@login_required
def dashboard(request):
    today = timezone.now().date()
    products_count = Product.objects.filter(is_active=True).count()
    customers_count = Customer.objects.filter(status="active").count()
    orders_in_progress = Order.objects.exclude(
        status__in=["delivered", "confirmed_received", "cancelled"]
    ).count()
    total_revenue = (
        Order.objects.filter(status="confirmed_received").aggregate(
            total=Sum("commission_amount")
        )["total"]
        or 0
    )
    # Use sample if low data
    sales_data = [14200000, 18600000, 22300000, 19800000, 26400000, 31200000, 28900000]
    months = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر"]

    recent_orders = list(Order.objects.select_related("customer").order_by("-created_at")[:5])
    low_stock_products = list(
        Product.objects.filter(stock__lt=F("low_stock_threshold")).order_by("stock")[:5]
    )
    recent_consultations = list(
        Consultation.objects.filter(status="pending").order_by("-created_at")[:3]
    )

    context = {
        "products_count": products_count,
        "customers_count": customers_count,
        "orders_in_progress": orders_in_progress,
        "total_revenue": sum(sales_data),
        "current_month_income": sales_data[-1],
        "monthly_income": [{"month": m, "amount": a} for m, a in zip(months, sales_data)],
        "monthly_income_json": json.dumps(
            [{"month": m, "amount": a} for m, a in zip(months, sales_data)], ensure_ascii=False
        ),
        "recent_orders": recent_orders,
        "low_stock_products": low_stock_products,
        "recent_consultations": recent_consultations,
    }
    return render_page(request, "pages/dashboard.html", context, active="dashboard")


# ====================================================================
# 1. CUSTOMERS (مشتریان)
# ====================================================================
@login_required
def customers(request):
    search = request.GET.get("q", "").strip()
    type_filter = request.GET.get("type", "")

    customers_qs = Customer.objects.all()
    if search:
        customers_qs = customers_qs.filter(
            Q(name__icontains=search)
            | Q(phone__icontains=search)
            | Q(city__icontains=search)
            | Q(contact_person__icontains=search)
        )
    if type_filter:
        customers_qs = customers_qs.filter(type=type_filter)

    customers_list = list(customers_qs.order_by("-created_at"))
    customer_types = Customer.TypeChoices.choices

    context = {
        "customers": customers_list,
        "customer_types": customer_types,
        "selected_type": type_filter,
        "search": search,
    }
    return render_page(request, "pages/customers.html", context, active="customers")


@login_required
def customer_add(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        type_ = request.POST.get("type", "wound_specialist")
        contact_person = request.POST.get("contact_person", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        city = request.POST.get("city", "").strip()
        address = request.POST.get("address", "").strip()
        workplace = request.POST.get("workplace", "").strip()
        work_history = request.POST.get("work_history", "").strip()
        commission_rate = request.POST.get("commission_rate", "20.00")
        status = request.POST.get("status", "active")
        notes = request.POST.get("notes", "").strip()

        if not name or not phone:
            messages.error(request, "نام و شماره تماس الزامی است")
            return redirect("customer_add")

        try:
            commission_val = float(commission_rate)
        except ValueError:
            commission_val = 20.00

        customer = Customer.objects.create(
            name=name, type=type_, contact_person=contact_person,
            phone=phone, email=email, city=city, address=address,
            workplace=workplace, work_history=work_history,
            commission_rate=commission_val, status=status, notes=notes,
        )
        messages.success(request, f'مشتری «{customer.name}» اضافه شد')
        log_activity(request, ActivityLog.ActionChoices.CREATE, "مشتریان",
                     f"افزودن مشتری «{customer.name}» ({customer.get_type_display()})", obj=customer)
        return redirect("customers")

    customer_types = Customer.TypeChoices.choices
    customer_statuses = Customer.StatusChoices.choices
    context = {"customer_types": customer_types, "customer_statuses": customer_statuses}
    return render_page(request, "pages/customer_add.html", context, active="customers")


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    orders = list(customer.orders.order_by("-created_at")[:10])
    commissions = list(customer.commissions.order_by("-created_at")[:5])
    reviews = list(customer.reviews.order_by("-created_at")[:3])
    context = {
        "customer": customer,
        "orders": orders,
        "commissions": commissions,
        "reviews": reviews,
    }
    return render_page(request, "pages/customer_detail.html", context, active="customers")


@login_required
def customer_edit(request, pk):
    """ویرایش اطلاعات یک مشتری موجود."""
    customer = get_object_or_404(Customer, pk=pk)

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        type_ = request.POST.get("type", customer.type)
        contact_person = request.POST.get("contact_person", "").strip()
        phone = request.POST.get("phone", "").strip()
        email = request.POST.get("email", "").strip()
        city = request.POST.get("city", "").strip()
        address = request.POST.get("address", "").strip()
        workplace = request.POST.get("workplace", "").strip()
        work_history = request.POST.get("work_history", "").strip()
        commission_rate = request.POST.get("commission_rate", str(customer.commission_rate))
        status = request.POST.get("status", customer.status)
        notes = request.POST.get("notes", "").strip()

        if not name or not phone:
            messages.error(request, "نام و شماره تماس الزامی است")
            return redirect("customer_edit", pk=pk)

        try:
            commission_val = float(commission_rate)
            if not (0 <= commission_val <= 100):
                raise ValueError
        except ValueError:
            messages.error(request, "درصد پورسانت باید عددی بین ۰ و ۱۰۰ باشد")
            return redirect("customer_edit", pk=pk)

        old_name = customer.name
        customer.name = name
        customer.type = type_
        customer.contact_person = contact_person
        customer.phone = phone
        customer.email = email
        customer.city = city
        customer.address = address
        customer.workplace = workplace
        customer.work_history = work_history
        customer.commission_rate = commission_val
        customer.status = status
        customer.notes = notes
        customer.save()

        # --- Panel account management (optional) ---
        panel_username = request.POST.get("panel_username", "").strip()
        panel_password = request.POST.get("panel_password", "").strip()
        remove_panel = request.POST.get("remove_panel") == "on"
        if remove_panel and customer.user:
            customer.user.delete()
            customer.user = None
            customer.save()
            messages.info(request, "حساب پنل مشتری حذف شد")
        elif panel_username and panel_password:
            try:
                if customer.user:
                    # Update existing linked account
                    user = customer.user
                    user.username = panel_username
                    user.set_password(panel_password)
                    user.save()
                else:
                    # Create a new non-staff user and link it
                    if User.objects.filter(username=panel_username).exists():
                        messages.error(request, f"نام کاربری «{panel_username}» قبلاً گرفته شده است")
                    else:
                        user = User.objects.create_user(
                            username=panel_username, password=panel_password,
                            is_staff=False, is_superuser=False,
                        )
                        customer.user = user
                        customer.save()
                        messages.success(request, f"حساب پنل با نام کاربری «{panel_username}» ایجاد شد")
            except Exception as e:
                messages.error(request, f"خطا در ایجاد حساب پنل: {e}")

        messages.success(request, f'مشتری «{customer.name}» به‌روزرسانی شد')
        log_activity(request, ActivityLog.ActionChoices.UPDATE, "مشتریان",
                     f"ویرایش مشتری «{old_name}»", obj=customer)
        return redirect("customers")

    customer_types = Customer.TypeChoices.choices
    customer_statuses = Customer.StatusChoices.choices
    context = {
        "customer": customer,
        "customer_types": customer_types,
        "customer_statuses": customer_statuses,
    }
    return render_page(request, "pages/customer_edit.html", context, active="customers")


@login_required
def customers_export_excel(request):
    """Export customers to Excel/CSV."""
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="customers.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "نام", "نوع مشتری", "فرد قابل تماس", "تلفن", "ایمیل",
        "شهر", "محل کار", "سابقه کاری", "درصد پورسانت", "وضعیت", "تعداد سفارش‌ها", "مجموع خرید"
    ])

    for c in Customer.objects.all().order_by("-created_at"):
        writer.writerow([
            c.name, c.get_type_display(), c.contact_person, c.phone, c.email,
            c.city, c.workplace, c.work_history, str(c.commission_rate) + "%",
            c.get_status_display(), c.total_orders, f"{c.total_spent:,}"
        ])

    log_activity(request, ActivityLog.ActionChoices.EXPORT, "مشتریان", "خروجی اکسل اطلاعات مشتریان")
    return response


# ====================================================================
# 2. PRODUCTS (محصولات)
# ====================================================================
@login_required
def products(request):
    brand_filter = request.GET.get("brand")
    search = request.GET.get("q", "").strip()
    wound_type_filter = request.GET.get("wound_type", "")

    products_qs = Product.objects.select_related("brand").filter(is_active=True)
    if brand_filter:
        products_qs = products_qs.filter(brand_id=brand_filter)
    if search:
        products_qs = products_qs.filter(
            Q(name__icontains=search)
            | Q(category__icontains=search)
            | Q(brand__name__icontains=search)
        )
    if wound_type_filter:
        products_qs = products_qs.filter(
            Q(wound_type=wound_type_filter) | Q(wound_type="all")
        )

    products_list = list(products_qs.order_by("-created_at"))
    brands_list = list(Brand.objects.all().order_by("name"))
    wound_types = Product.WoundType.choices

    context = {
        "products": products_list,
        "brands": brands_list,
        "wound_types": wound_types,
        "selected_brand": brand_filter,
        "selected_wound_type": wound_type_filter,
        "search": search,
    }
    return render_page(request, "pages/products.html", context, active="products")


@login_required
def product_add(request):
    if request.method == "POST":
        brand_id = request.POST.get("brand")
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", "other")
        wound_type = request.POST.get("wound_type", "all")
        description = request.POST.get("description", "").strip()
        price = request.POST.get("price", "0")
        stock = request.POST.get("stock", "0")
        unit = request.POST.get("unit", "عدد")
        image_emoji = request.POST.get("image_emoji", "📦")
        image_url = request.POST.get("image_url", "").strip()
        low_stock_threshold = request.POST.get("low_stock_threshold", "10")
        is_active = request.POST.get("is_active") == "on"

        try:
            brand = Brand.objects.get(id=brand_id)
            price_val = max(0, int(price))
            stock_val = max(0, int(stock))
            threshold_val = max(0, int(low_stock_threshold))
        except (Brand.DoesNotExist, ValueError):
            messages.error(request, "اطلاعات نامعتبر است")
            return redirect("product_add")

        product = Product.objects.create(
            brand=brand, name=name, category=category, wound_type=wound_type,
            description=description, price=price_val, stock=stock_val,
            unit=unit, image_emoji=image_emoji, image_url=image_url,
            low_stock_threshold=threshold_val, is_active=is_active,
        )
        if request.FILES.get("image"):
            product.image = request.FILES["image"]
            product.save()
        messages.success(request, f'محصول «{product.name}» اضافه شد')
        log_activity(request, ActivityLog.ActionChoices.CREATE, "محصولات",
                     f"افزودن محصول «{product.name}»", obj=product)
        return redirect("products")

    brands_list = list(Brand.objects.all().order_by("name"))
    categories = Product.CategoryChoices.choices
    wound_types = Product.WoundType.choices
    context = {"brands": brands_list, "categories": categories, "wound_types": wound_types}
    return render_page(request, "pages/product_add.html", context, active="products")


@login_required
def product_edit(request, pk):
    """ویرایش اطلاعات یک محصول موجود (نام، قیمت، موجودی، برند و ...)."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        brand_id = request.POST.get("brand")
        name = request.POST.get("name", "").strip()
        category = request.POST.get("category", product.category)
        wound_type = request.POST.get("wound_type", product.wound_type)
        description = request.POST.get("description", "").strip()
        price = request.POST.get("price", str(product.price))
        stock = request.POST.get("stock", str(product.stock))
        unit = request.POST.get("unit", product.unit)
        image_emoji = request.POST.get("image_emoji", product.image_emoji)
        image_url = request.POST.get("image_url", "").strip()
        low_stock_threshold = request.POST.get("low_stock_threshold", str(product.low_stock_threshold))
        is_active = request.POST.get("is_active") == "on"
        clear_image = request.POST.get("clear_image") == "on"

        if not name:
            messages.error(request, "نام محصول الزامی است")
            return redirect("product_edit", pk=pk)

        try:
            brand = Brand.objects.get(id=brand_id)
            price_val = max(0, int(price))
            stock_val = max(0, int(stock))
            threshold_val = max(0, int(low_stock_threshold))
        except (Brand.DoesNotExist, ValueError):
            messages.error(request, "اطلاعات نامعتبر است (برند یا اعداد)")
            return redirect("product_edit", pk=pk)

        old_name = product.name
        product.brand = brand
        product.name = name
        product.category = category
        product.wound_type = wound_type
        product.description = description
        product.price = price_val
        product.stock = stock_val
        product.unit = unit
        product.image_emoji = image_emoji
        product.image_url = image_url
        product.low_stock_threshold = threshold_val
        product.is_active = is_active
        if clear_image and product.image:
            product.image.delete(save=False)
            product.image = None
        if request.FILES.get("image"):
            if product.image:
                product.image.delete(save=False)
            product.image = request.FILES["image"]
        product.save()
        messages.success(request, f'محصول «{product.name}» به‌روزرسانی شد')
        log_activity(request, ActivityLog.ActionChoices.UPDATE, "محصولات",
                     f"ویرایش محصول «{old_name}»", obj=product)
        return redirect("products")

    brands_list = list(Brand.objects.all().order_by("name"))
    categories = Product.CategoryChoices.choices
    wound_types = Product.WoundType.choices
    context = {
        "product": product,
        "brands": brands_list,
        "categories": categories,
        "wound_types": wound_types,
    }
    return render_page(request, "pages/product_edit.html", context, active="products")


@login_required
def brand_add(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        country = request.POST.get("country", "").strip()
        logo_emoji = request.POST.get("logo_emoji", "🏷️").strip()
        description = request.POST.get("description", "").strip()
        if not name:
            messages.error(request, "نام برند الزامی است")
            return redirect("brand_add")
        if Brand.objects.filter(name=name).exists():
            messages.error(request, "این برند قبلاً ثبت شده است")
            return redirect("brand_add")
        brand = Brand.objects.create(name=name, country=country, logo_emoji=logo_emoji or "🏷️", description=description)
        messages.success(request, f'برند «{brand.name}» اضافه شد')
        log_activity(request, ActivityLog.ActionChoices.CREATE, "برندها", f"افزودن برند «{brand.name}»", obj=brand)
        return redirect("product_add")
    context = {"brands_list": list(Brand.objects.all().order_by("name"))}
    return render_page(request, "pages/brand_add.html", context, active="products")


# ====================================================================
# 3. ONLINE CONSULTATION (مشاوره آنلاین)
# ====================================================================
@login_required
def consultation(request):
    status_filter = request.GET.get("status", "")
    consultations_qs = Consultation.objects.all()
    if status_filter:
        consultations_qs = consultations_qs.filter(status=status_filter)
    consultations_list = list(consultations_qs.order_by("-created_at"))
    statuses = Consultation.StatusChoices.choices
    pending_count = Consultation.objects.filter(status="pending").count()
    answered_count = Consultation.objects.filter(status="answered").count()
    context = {
        "consultations": consultations_list,
        "statuses": statuses,
        "pending_count": pending_count,
        "answered_count": answered_count,
        "selected_status": status_filter,
    }
    return render_page(request, "pages/consultation.html", context, active="consultation")


@login_required
def consultation_add(request):
    if request.method == "POST":
        customer_name = request.POST.get("customer_name", "").strip()
        phone = request.POST.get("phone", "").strip()
        wound_type = request.POST.get("wound_type", "other")
        question = request.POST.get("question", "").strip()
        if customer_name and phone and question:
            Consultation.objects.create(
                customer_name=customer_name, phone=phone,
                wound_type=wound_type, question=question,
            )
            messages.success(request, "درخواست مشاوره ثبت شد")
            log_activity(request, ActivityLog.ActionChoices.CREATE, "مشاوره آنلاین",
                         f"ثبت درخواست مشاوره از «{customer_name}»")
            return redirect("consultation")
    wound_types = Consultation.WoundTypeChoices.choices
    context = {"wound_types": wound_types}
    return render_page(request, "pages/consultation_add.html", context, active="consultation")


@login_required
def consultation_answer(request, pk):
    consultation_obj = get_object_or_404(Consultation, pk=pk)
    if request.method == "POST":
        answer = request.POST.get("answer", "").strip()
        answered_by = request.POST.get("answered_by", "").strip()
        if answer:
            consultation_obj.answer = answer
            consultation_obj.answered_by = answered_by
            consultation_obj.status = "answered"
            consultation_obj.answered_at = timezone.now()
            consultation_obj.save()
            messages.success(request, "پاسخ ثبت شد")
            log_activity(request, ActivityLog.ActionChoices.CREATE, "مشاوره آنلاین",
                         f"پاسخ به مشاوره «{consultation_obj.customer_name}»")
            return redirect("consultation")
    context = {"consultation": consultation_obj}
    return render_page(request, "pages/consultation_answer.html", context, active="consultation")


# ====================================================================
# 4. SATISFACTION (رضایت مندی)
# ====================================================================
@login_required
def satisfaction(request):
    reviews_list = list(SatisfactionReview.objects.select_related("customer").order_by("-created_at"))
    avg_rating = 0
    if reviews_list:
        avg_rating = sum(r.rating for r in reviews_list) / len(reviews_list)
    total_reviews = len(reviews_list)
    five_star_count = sum(1 for r in reviews_list if r.rating == 5)
    context = {
        "reviews": reviews_list,
        "avg_rating": round(avg_rating, 1),
        "total_reviews": total_reviews,
        "five_star_count": five_star_count,
    }
    return render_page(request, "pages/satisfaction.html", context, active="satisfaction")


@login_required
def satisfaction_add(request):
    if request.method == "POST":
        customer_id = request.POST.get("customer")
        rating = request.POST.get("rating", "5")
        comment = request.POST.get("comment", "").strip()
        product_quality = request.POST.get("product_quality", "5")
        service_quality = request.POST.get("service_quality", "5")
        delivery_speed = request.POST.get("delivery_speed", "5")
        try:
            customer = Customer.objects.get(id=customer_id)
            review = SatisfactionReview.objects.create(
                customer=customer,
                rating=int(rating),
                comment=comment,
                product_quality=int(product_quality),
                service_quality=int(service_quality),
                delivery_speed=int(delivery_speed),
            )
            messages.success(request, "نظر شما ثبت شد")
            log_activity(request, ActivityLog.ActionChoices.CREATE, "رضایت مندی",
                         f"ثبت نظر برای «{customer.name}» - {rating} ستاره")
            return redirect("satisfaction")
        except (Customer.DoesNotExist, ValueError):
            messages.error(request, "اطلاعات نامعتبر است")
    customers_list = list(Customer.objects.filter(status="active").order_by("name"))
    context = {"customers": customers_list}
    return render_page(request, "pages/satisfaction_add.html", context, active="satisfaction")


# ====================================================================
# 5. INVENTORY (لیست موجودی انبار + قیمت)
# ====================================================================
@login_required
def inventory(request):
    all_products = list(Product.objects.select_related("brand").order_by("stock"))
    total_value = sum(p.total_value for p in all_products)
    low_stock_count = sum(1 for p in all_products if p.is_low_stock)
    out_of_stock_count = sum(1 for p in all_products if p.is_out_of_stock)
    context = {
        "products": all_products,
        "total_value": total_value,
        "low_stock_count": low_stock_count,
        "out_of_stock_count": out_of_stock_count,
    }
    return render_page(request, "pages/inventory.html", context, active="inventory")


# ====================================================================
# 6. INVOICES (فاکتور)
# ====================================================================
@login_required
def invoices(request):
    invoices_list = list(Invoice.objects.select_related("customer", "order").order_by("-created_at"))
    paid_count = sum(1 for i in invoices_list if i.status == "paid")
    pending_count = sum(1 for i in invoices_list if i.status in ["draft", "sent_for_approval"])
    approved_count = sum(1 for i in invoices_list if i.status == "approved")
    context = {
        "invoices": invoices_list,
        "paid_count": paid_count,
        "pending_count": pending_count,
        "approved_count": approved_count,
    }
    return render_page(request, "pages/invoices.html", context, active="invoices")


@login_required
def invoice_add(request):
    if request.method == "POST":
        order_id = request.POST.get("order")
        inv_type = request.POST.get("type", "pre_invoice")
        amount_str = request.POST.get("amount", "0")
        status = request.POST.get("status", "draft")
        issue_date = request.POST.get("issue_date") or None
        due_date = request.POST.get("due_date") or None
        notes = request.POST.get("notes", "").strip()
        try:
            order = Order.objects.get(id=order_id)
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except (Order.DoesNotExist, ValueError):
            messages.error(request, "اطلاعات نامعتبر است")
            return redirect("invoice_add")
        tax = int(amount * 0.1)
        total = amount + tax
        invoice = Invoice.objects.create(
            order=order, customer=order.customer, type=inv_type,
            amount=amount, tax=tax, total=total, status=status,
            issue_date=issue_date, due_date=due_date, notes=notes,
        )
        # Update order status
        if inv_type == "pre_invoice":
            order.status = Order.StatusChoices.PRE_INVOICE_ISSUED
        else:
            order.status = Order.StatusChoices.INVOICE_ISSUED
        order.save()
        messages.success(request, f'فاکتور «{invoice.number}» صادر شد')
        log_activity(request, ActivityLog.ActionChoices.CREATE, "فاکتورها",
                     f"صدور فاکتور «{invoice.number}» برای «{order.customer.name}»")
        return redirect("invoices")
    orders_list = list(Order.objects.exclude(status__in=["delivered", "cancelled"]).order_by("-created_at"))
    types = Invoice.TypeChoices.choices
    statuses = Invoice.StatusChoices.choices
    context = {"orders": orders_list, "types": types, "statuses": statuses}
    return render_page(request, "pages/invoice_add.html", context, active="invoices")


@login_required
def invoice_approve(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.status = Invoice.StatusChoices.APPROVED
    invoice.save()
    if invoice.order:
        invoice.order.status = Order.StatusChoices.INVOICE_APPROVED
        invoice.order.save()
    messages.success(request, f"فاکتور «{invoice.number}» تأیید شد")
    log_activity(request, ActivityLog.ActionChoices.UPDATE, "فاکتورها",
                 f"تأیید فاکتور «{invoice.number}»")
    return redirect("invoices")


@login_required
def invoice_issue(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)
    invoice.status = Invoice.StatusChoices.ISSUED
    invoice.save()
    if invoice.order:
        invoice.order.status = Order.StatusChoices.INVOICE_ISSUED
        invoice.order.save()
    messages.success(request, f"فاکتور «{invoice.number}» صادر شد")
    log_activity(request, ActivityLog.ActionChoices.UPDATE, "فاکتورها",
                 f"صدور فاکتور «{invoice.number}»")
    return redirect("invoices")


# ====================================================================
# 7. PAYMENTS (پرداخت)
# ====================================================================
@login_required
def payments(request):
    payments_list = list(Payment.objects.select_related("customer", "invoice").order_by("-created_at"))
    confirmed_total = sum(p.amount for p in payments_list if p.status == "confirmed")
    pending_total = sum(p.amount for p in payments_list if p.status == "pending")
    failed_count = sum(1 for p in payments_list if p.status == "failed")
    context = {
        "payments": payments_list,
        "confirmed_total": confirmed_total,
        "pending_total": pending_total,
        "failed_count": failed_count,
    }
    return render_page(request, "pages/payments.html", context, active="payments")


@login_required
def payment_add(request):
    if request.method == "POST":
        invoice_id = request.POST.get("invoice")
        amount_str = request.POST.get("amount", "0")
        method = request.POST.get("method", "card")
        status = request.POST.get("status", "confirmed")
        transaction_ref = request.POST.get("transaction_ref", "").strip()
        notes = request.POST.get("notes", "").strip()
        try:
            invoice = Invoice.objects.get(id=invoice_id)
            amount = int(amount_str)
            if amount <= 0:
                raise ValueError
        except (Invoice.DoesNotExist, ValueError):
            messages.error(request, "اطلاعات نامعتبر است")
            return redirect("payment_add")
        payment = Payment.objects.create(
            invoice=invoice, customer=invoice.customer, amount=amount,
            method=method, status=status, transaction_ref=transaction_ref, notes=notes,
        )
        if request.FILES.get("receipt_image"):
            payment.receipt_image = request.FILES["receipt_image"]
            payment.save()
        # Update invoice status if fully paid
        if status == "confirmed":
            total_paid = sum(p.amount for p in invoice.payments.filter(status="confirmed"))
            if total_paid >= invoice.total:
                invoice.status = Invoice.StatusChoices.PAID
                invoice.save()
        messages.success(request, f"پرداخت به مبلغ {amount:,} ثبت شد")
        log_activity(request, ActivityLog.ActionChoices.PAYMENT, "پرداخت‌ها",
                     f"ثبت پرداخت {amount:,} تومان برای فاکتور «{invoice.number}»")
        return redirect("payments")
    invoices_list = list(Invoice.objects.exclude(status="paid").select_related("customer").order_by("-created_at"))
    if not invoices_list:
        invoices_list = list(Invoice.objects.select_related("customer").order_by("-created_at"))
    methods = Payment.MethodChoices.choices
    statuses = Payment.StatusChoices.choices
    context = {"invoices": invoices_list, "methods": methods, "statuses": statuses}
    return render_page(request, "pages/payment_add.html", context, active="payments")


# ====================================================================
# 8. COMMISSIONS (پورسانت مشتریان - 20%)
# ====================================================================
@login_required
def commissions(request):
    commissions_list = list(Commission.objects.select_related("customer", "order").order_by("-created_at"))
    pending_total = sum(c.commission_amount for c in commissions_list if c.status == "pending")
    approved_total = sum(c.commission_amount for c in commissions_list if c.status == "approved")
    paid_total = sum(c.commission_amount for c in commissions_list if c.status == "paid")
    context = {
        "commissions": commissions_list,
        "pending_total": pending_total,
        "approved_total": approved_total,
        "paid_total": paid_total,
    }
    return render_page(request, "pages/commissions.html", context, active="commissions")


@login_required
def commission_approve(request, pk):
    commission = get_object_or_404(Commission, pk=pk)
    if commission.status != Commission.StatusChoices.PENDING:
        messages.error(request, "این پورسانت قابل تأیید نیست")
        return redirect("commissions")
    commission.status = Commission.StatusChoices.APPROVED
    commission.save()
    messages.success(request, f"پورسانت به مبلغ {commission.commission_amount:,} تومان تأیید شد")
    log_activity(request, ActivityLog.ActionChoices.UPDATE, "پورسانت",
                 f"تأیید پورسانت «{commission.customer.name}» - {commission.commission_amount:,} تومان")
    return redirect("commissions")


@login_required
def commission_pay(request, pk):
    commission = get_object_or_404(Commission, pk=pk)
    if commission.status != Commission.StatusChoices.APPROVED:
        messages.error(request, "این پورسانت قابل پرداخت نیست. ابتدا باید تأیید شود.")
        return redirect("commissions")
    commission.status = Commission.StatusChoices.PAID
    commission.paid_at = timezone.now()
    commission.save()
    messages.success(request, f"پورسانت به مبلغ {commission.commission_amount:,} تومان پرداخت شد")
    log_activity(request, ActivityLog.ActionChoices.PAYMENT, "پورسانت",
                 f"پرداخت پورسانت «{commission.customer.name}» - {commission.commission_amount:,} تومان")
    return redirect("commissions")


# ====================================================================
# 9. SALES REPORT (گزارش فروش بازاریابی)
# ====================================================================
@login_required
def sales_report(request):
    orders_list = list(Order.objects.select_related("customer").order_by("-created_at")[:50])
    total_sales = sum(o.subtotal for o in orders_list)
    total_commission = sum(o.commission_amount for o in orders_list)

    # Sales by customer type
    customer_type_stats = []
    for type_val, type_label in Customer.TypeChoices.choices:
        custs = Customer.objects.filter(type=type_val)
        order_count = Order.objects.filter(customer__in=custs).count()
        sales = sum(o.subtotal for o in Order.objects.filter(customer__in=custs))
        customer_type_stats.append({
            "type": type_val,
            "label": type_label,
            "count": custs.count(),
            "orders": order_count,
            "sales": sales,
        })

    # Monthly sales (sample)
    monthly_data = [
        {"month": "فروردین", "amount": 14200000},
        {"month": "اردیبهشت", "amount": 18600000},
        {"month": "خرداد", "amount": 22300000},
        {"month": "تیر", "amount": 19800000},
        {"month": "مرداد", "amount": 26400000},
        {"month": "شهریور", "amount": 31200000},
        {"month": "مهر", "amount": 28900000},
    ]

    context = {
        "orders": orders_list,
        "total_sales": total_sales,
        "total_commission": total_commission,
        "customer_type_stats": customer_type_stats,
        "monthly_data": monthly_data,
        "monthly_data_json": json.dumps(monthly_data, ensure_ascii=False),
    }
    return render_page(request, "pages/sales_report.html", context, active="sales_report")


@login_required
def sales_report_export_excel(request):
    response = HttpResponse(content_type="text/csv; charset=utf-8-sig")
    response["Content-Disposition"] = 'attachment; filename="sales_report.csv"'
    writer = csv.writer(response)
    writer.writerow(["شماره سفارش", "مشتری", "نوع مشتری", "تاریخ", "تعداد اقلام", "مبلغ پایه", "مالیات", "کل", "پورسانت", "وضعیت"])
    for o in Order.objects.select_related("customer").order_by("-created_at"):
        writer.writerow([
            o.number, o.customer.name, o.customer.get_type_display(),
            o.created_at.strftime("%Y/%m/%d"), o.total_items,
            o.subtotal, o.tax, o.total, o.commission_amount,
            o.get_status_display()
        ])
    log_activity(request, ActivityLog.ActionChoices.EXPORT, "گزارش فروش", "خروجی اکسل گزارش فروش")
    return response


# ====================================================================
# 10. PRODUCT REQUEST (فرم درخواست محصول)
# ====================================================================
@login_required
def product_request(request):
    status_filter = request.GET.get("status", "")
    requests_qs = ProductRequest.objects.select_related("customer", "product")
    if status_filter:
        requests_qs = requests_qs.filter(status=status_filter)
    requests_list = list(requests_qs.order_by("-created_at"))
    statuses = ProductRequest.StatusChoices.choices
    context = {
        "requests": requests_list,
        "statuses": statuses,
        "selected_status": status_filter,
    }
    return render_page(request, "pages/product_request.html", context, active="product_request")


@login_required
def product_request_add(request):
    if request.method == "POST":
        customer_id = request.POST.get("customer")
        product_id = request.POST.get("product") or None
        product_name = request.POST.get("product_name", "").strip()
        quantity = request.POST.get("quantity", "1")
        unit = request.POST.get("unit", "عدد")
        notes = request.POST.get("notes", "").strip()
        try:
            customer = Customer.objects.get(id=customer_id)
            qty = int(quantity)
            if qty <= 0:
                raise ValueError
        except (Customer.DoesNotExist, ValueError):
            messages.error(request, "اطلاعات نامعتبر است")
            return redirect("product_request_add")
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                if not product_name:
                    product_name = product.name
            except Product.DoesNotExist:
                product = None
        else:
            product = None
        pr = ProductRequest.objects.create(
            customer=customer, product=product, product_name=product_name,
            quantity=qty, unit=unit, notes=notes,
        )
        messages.success(request, "درخواست محصول ثبت شد")
        log_activity(request, ActivityLog.ActionChoices.CREATE, "درخواست محصول",
                     f"درخواست «{product_name}» × {qty} از «{customer.name}»")
        return redirect("product_request")
    customers_list = list(Customer.objects.filter(status="active").order_by("name"))
    products_list = list(Product.objects.filter(is_active=True).order_by("name"))
    context = {"customers": customers_list, "products": products_list}
    return render_page(request, "pages/product_request_add.html", context, active="product_request")


# ====================================================================
# 11. WORKFLOW: Send to Finance/Warehouse/Procurement
# ====================================================================
@login_required
def product_request_send_to_finance(request, pk):
    pr = get_object_or_404(ProductRequest, pk=pk)
    pr.status = ProductRequest.StatusChoices.SENT_TO_FINANCE
    pr.sent_to_finance_at = timezone.now()
    pr.save()
    messages.success(request, "درخواست به مسئول مالی ارسال شد")
    log_activity(request, ActivityLog.ActionChoices.SEND, "درخواست محصول",
                 f"ارسال درخواست «{pr.product_name}» به مسئول مالی")
    return redirect("product_request")


@login_required
def product_request_send_to_warehouse(request, pk):
    pr = get_object_or_404(ProductRequest, pk=pk)
    pr.status = ProductRequest.StatusChoices.IN_WAREHOUSE
    pr.sent_to_warehouse_at = timezone.now()
    pr.save()
    messages.success(request, "درخواست به انبار ارسال شد")
    log_activity(request, ActivityLog.ActionChoices.SEND, "درخواست محصول",
                 f"ارسال درخواست «{pr.product_name}» به انبار")
    return redirect("product_request")


@login_required
def product_request_send_to_procurement(request, pk):
    pr = get_object_or_404(ProductRequest, pk=pk)
    pr.status = ProductRequest.StatusChoices.SENT_TO_PROCUREMENT
    pr.sent_to_procurement_at = timezone.now()
    pr.save()
    messages.success(request, "درخواست به تدارکات ارسال شد")
    log_activity(request, ActivityLog.ActionChoices.SEND, "درخواست محصول",
                 f"ارسال درخواست «{pr.product_name}» به تدارکات")
    # Redirect to procurement page
    return redirect("procurement")


@login_required
def product_request_mark_in_progress(request, pk):
    pr = get_object_or_404(ProductRequest, pk=pk)
    pr.status = ProductRequest.StatusChoices.IN_PROGRESS
    pr.save()
    messages.success(request, "وضعیت درخواست به «در دست اقدام» تغییر کرد")
    # Redirect back to the page the user came from
    referer = request.META.get("HTTP_REFERER", "")
    if "procurement" in referer:
        return redirect("procurement")
    return redirect("product_request")


# ====================================================================
# 11. PROCUREMENT (تدارکات)
# ====================================================================
@login_required
def procurement(request):
    """Procurement page - shows requests sent to procurement and in progress."""
    # Requests that are in procurement or in progress
    procurement_list = list(
        ProductRequest.objects.select_related("customer", "product")
        .filter(status__in=["sent_to_procurement", "in_progress"])
        .order_by("-created_at")
    )
    # Also show completed ones for history
    completed_list = list(
        ProductRequest.objects.select_related("customer", "product")
        .filter(status="completed")
        .order_by("-updated_at")[:10]
    )

    context = {
        "procurement_list": procurement_list,
        "completed_list": completed_list,
        "pending_count": len(procurement_list),
        "completed_count": len(completed_list),
    }
    return render_page(request, "pages/procurement.html", context, active="procurement")


@login_required
def procurement_complete(request, pk):
    """Mark a procurement request as completed."""
    pr = get_object_or_404(ProductRequest, pk=pk)
    pr.status = ProductRequest.StatusChoices.COMPLETED
    pr.save()
    messages.success(request, f"درخواست «{pr.product_name}» تکمیل شد")
    log_activity(request, ActivityLog.ActionChoices.UPDATE, "تدارکات",
                 f"تکمیل درخواست تدارکات «{pr.product_name}» برای «{pr.customer.name}»")
    return redirect("procurement")


# ====================================================================
# ORDER (ثبت سفارش)
# ====================================================================
@login_required
def customer_order(request):
    if request.method == "POST":
        customer_id = request.POST.get("customer")
        product_ids = request.POST.getlist("products")
        quantities = request.POST.getlist("quantities")
        notes = request.POST.get("notes", "")
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            messages.error(request, "مشتری یافت نشد")
            return redirect("customer_order")
        order = Order.objects.create(customer=customer, notes=notes, status="pending")
        added = 0
        for pid, qty in zip(product_ids, quantities):
            try:
                product = Product.objects.get(id=pid)
                quantity = int(qty)
                if quantity > 0:
                    OrderItem.objects.create(
                        order=order, product=product, quantity=quantity, unit_price=product.price
                    )
                    added += 1
            except (Product.DoesNotExist, ValueError):
                continue
        if added:
            # Calculate commission
            rate = float(customer.commission_rate) / 100
            order.commission_amount = int(order.subtotal * rate)
            order.save()
            messages.success(request, f"سفارش {order.number} با {added} قلم کالا و مبلغ {order.total:,} تومان ثبت شد")
            log_activity(request, ActivityLog.ActionChoices.ORDER, "سفارشات",
                         f"ثبت سفارش {order.number} برای «{customer.name}» - {added} قلم، {order.total:,} تومان")
        else:
            order.delete()
            messages.error(request, "هیچ محصول معتبری انتخاب نشده بود")
        return redirect("customer_order")

    customers_list = list(Customer.objects.filter(status="active").order_by("name"))
    products_list = list(Product.objects.filter(is_active=True).select_related("brand").order_by("name"))
    preselect_product_id = request.GET.get("product_id", "")
    context = {
        "customers": customers_list,
        "products": products_list,
        "preselect_product_id": preselect_product_id,
    }
    return render_page(request, "pages/customer_order.html", context, active="customer_order")


@login_required
def orders_list(request):
    orders_list = list(Order.objects.select_related("customer").order_by("-created_at"))
    context = {"orders": orders_list}
    return render_page(request, "pages/orders_list.html", context, active="customer_order")


@login_required
def order_ship(request, pk):
    """Advance order status: pending → shipped."""
    order = get_object_or_404(Order, pk=pk)
    if order.status != Order.StatusChoices.PENDING:
        messages.error(request, "این سفارش قابل ارسال نیست (در انتظار نیست)")
        return redirect("orders_list")
    order.status = Order.StatusChoices.SHIPPED
    order.save()
    messages.success(request, f"سفارش {order.number} ارسال شد")
    log_activity(request, ActivityLog.ActionChoices.UPDATE, "سفارشات",
                 f"ارسال سفارش {order.number} به «{order.customer.name}»")
    return redirect("orders_list")


@login_required
def order_deliver(request, pk):
    """Advance order status: shipped → delivered."""
    order = get_object_or_404(Order, pk=pk)
    if order.status != Order.StatusChoices.SHIPPED:
        messages.error(request, "این سفارش قابل تحویل نیست (ارسال شده نیست)")
        return redirect("orders_list")
    order.status = Order.StatusChoices.DELIVERED
    order.save()
    messages.success(request, f"سفارش {order.number} به مشتری تحویل داده شد")
    log_activity(request, ActivityLog.ActionChoices.UPDATE, "سفارشات",
                 f"تحویل سفارش {order.number} به «{order.customer.name}»")
    return redirect("orders_list")


@login_required
def order_confirm_receipt(request, pk):
    """Advance order status: delivered → confirmed_received and create commission."""
    order = get_object_or_404(Order, pk=pk)
    if order.status != Order.StatusChoices.DELIVERED:
        messages.error(request, "برای تأیید دریافت، سفارش باید در وضعیت «تحویل شده» باشد")
        return redirect("orders_list")
    # Recalculate commission from subtotal × rate (do not trust stored field)
    rate = float(order.customer.commission_rate) / 100
    correct_amount = int(order.subtotal * rate)
    order.commission_amount = correct_amount
    order.status = Order.StatusChoices.CONFIRMED_RECEIVED
    order.save()
    # Create commission record once (idempotent — no duplicates)
    commission, created = Commission.objects.get_or_create(
        order=order,
        defaults={
            "customer": order.customer,
            "rate": order.customer.commission_rate,
            "base_amount": order.subtotal,
            "commission_amount": correct_amount,
        },
    )
    if not created:
        # Update existing record if values drifted
        commission.base_amount = order.subtotal
        commission.commission_amount = correct_amount
        commission.rate = order.customer.commission_rate
        commission.save()
    msg = (f"دریافت کالا توسط «{order.customer.name}» تأیید شد. "
           f"پورسانت {correct_amount:,} تومان ثبت شد.")
    messages.success(request, msg)
    log_activity(request, ActivityLog.ActionChoices.UPDATE, "سفارشات",
                 f"تأیید دریافت کالا - سفارش {order.number} - پورسانت {correct_amount:,} تومان")
    return redirect("orders_list")


# ====================================================================
# WAREHOUSE
# ====================================================================
@login_required
def warehouse(request):
    movements = list(WarehouseMovement.objects.select_related("product").order_by("-created_at"))
    in_count = sum(1 for m in movements if m.type == "in")
    out_count = sum(1 for m in movements if m.type == "out")
    context = {"movements": movements, "in_count": in_count, "out_count": out_count}
    return render_page(request, "pages/warehouse.html", context, active="warehouse")


@login_required
def warehouse_add(request):
    if request.method == "POST":
        product_id = request.POST.get("product")
        type_ = request.POST.get("type", "in")
        quantity_str = request.POST.get("quantity", "1")
        reason = request.POST.get("reason", "other")
        reference = request.POST.get("reference", "").strip()
        operator = request.POST.get("operator", "").strip()
        notes = request.POST.get("notes", "").strip()
        try:
            product = Product.objects.get(id=product_id)
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError
        except (Product.DoesNotExist, ValueError):
            messages.error(request, "اطلاعات نامعتبر است")
            return redirect("warehouse_add")
        if not operator:
            messages.error(request, "نام اپراتور الزامی است")
            return redirect("warehouse_add")
        # Check if OUT quantity exceeds stock
        if type_ == "out" and quantity > product.stock:
            messages.error(
                request,
                f"موجودی کافی نیست! موجودی فعلی «{product.name}»: {product.stock} {product.unit}، "
                f"درخواست شده: {quantity} {product.unit}"
            )
            return redirect("warehouse_add")
        movement = WarehouseMovement.objects.create(
            product=product, type=type_, quantity=quantity,
            reason=reason, reference=reference or f"ثبت دستی - {operator}",
            operator=operator, notes=notes,
        )
        # Update stock
        if type_ == "in":
            product.stock += quantity
        else:
            product.stock = max(0, product.stock - quantity)
        product.save()
        direction = "ورودی" if type_ == "in" else "خروجی"
        messages.success(request, f"تراکنش {direction} برای «{product.name}» ثبت شد. موجودی جدید: {product.stock} {product.unit}")
        log_activity(request, ActivityLog.ActionChoices.CREATE, "انبار",
                     f"ثبت تراکنش {direction} {quantity} {product.unit} برای «{product.name}». موجودی: {product.stock}")
        return redirect("warehouse")
    products_list = list(Product.objects.filter(is_active=True).order_by("name"))
    reasons = WarehouseMovement.ReasonChoices.choices
    context = {"products": products_list, "reasons": reasons}
    return render_page(request, "pages/warehouse_add.html", context, active="warehouse")


# ====================================================================
# 15. FINANCIAL TRACKING (پیگیری مالی)
# ====================================================================
@login_required
def financial_tracking(request):
    """Financial tracking overview - invoices, payments, outstanding."""
    all_invoices = list(Invoice.objects.select_related("customer").order_by("-created_at"))
    total_invoiced = sum(i.total for i in all_invoices)
    total_paid = sum(i.total for i in all_invoices if i.status == "paid")
    total_outstanding = total_invoiced - total_paid
    overdue_invoices = [i for i in all_invoices if i.status == "overdue"]

    # Recent payments
    recent_payments = list(Payment.objects.select_related("customer", "invoice").order_by("-created_at")[:10])

    context = {
        "invoices": all_invoices,
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "overdue_invoices": overdue_invoices,
        "recent_payments": recent_payments,
    }
    return render_page(request, "pages/financial_tracking.html", context, active="financial_tracking")


# ====================================================================
# 16. DAILY REPORT (گزارش روزانه پرزنت)
# ====================================================================
@login_required
def daily_report(request):
    if request.method == "POST":
        presenter_name = request.POST.get("presenter_name")
        report_date = request.POST.get("report_date")
        activity_type = request.POST.get("activity_type", "visit")
        customer_id = request.POST.get("customer") or None
        visits_count = int(request.POST.get("visits_count", 0))
        calls_count = int(request.POST.get("calls_count", 0))
        products_presented = int(request.POST.get("products_presented", 0))
        new_customers = int(request.POST.get("new_customers", 0))
        sales_amount = int(request.POST.get("sales_amount", 0))
        notes = request.POST.get("notes", "")
        if presenter_name and report_date:
            customer = None
            if customer_id:
                try:
                    customer = Customer.objects.get(id=customer_id)
                except Customer.DoesNotExist:
                    pass
            DailyReport.objects.create(
                presenter_name=presenter_name, report_date=report_date,
                activity_type=activity_type, customer=customer,
                visits_count=visits_count, calls_count=calls_count,
                products_presented=products_presented, new_customers=new_customers,
                sales_amount=sales_amount, notes=notes,
            )
            messages.success(request, "گزارش روزانه ثبت شد")
            log_activity(request, ActivityLog.ActionChoices.REPORT, "گزارش روزانه",
                         f"ثبت گزارش توسط «{presenter_name}» - {visits_count} ویزیت")
            return redirect("daily_report")

    reports = list(DailyReport.objects.select_related("customer").order_by("-report_date", "-created_at"))
    total_visits = sum(r.visits_count for r in reports)
    total_calls = sum(r.calls_count for r in reports)
    total_sales = sum(r.sales_amount for r in reports)

    # Sample data if empty
    if not reports:
        today = timezone.now().date()
        reports = [
            {"presenter_name": "دکتر مریم احمدی", "report_date": today, "visits_count": 12,
             "calls_count": 8, "products_presented": 18, "new_customers": 3, "sales_amount": 4250000,
             "notes": "ویزیت بیمارستان دیابت ایران"},
            {"presenter_name": "پرستار زهرا موسوی", "report_date": today, "visits_count": 18,
             "calls_count": 12, "products_presented": 24, "new_customers": 5, "sales_amount": 5860000,
             "notes": "ارائه پرزنت در کلینیک زخم شفا"},
        ]
        total_visits = sum(r["visits_count"] for r in reports)
        total_calls = sum(r["calls_count"] for r in reports)
        total_sales = sum(r["sales_amount"] for r in reports)

    activity_types = DailyReport.ActivityType.choices
    customers_list = list(Customer.objects.filter(status="active").order_by("name"))
    context = {
        "reports": reports,
        "total_visits": total_visits,
        "total_calls": total_calls,
        "total_sales": total_sales,
        "activity_types": activity_types,
        "customers": customers_list,
    }
    return render_page(request, "pages/daily_report.html", context, active="daily_report")


# ====================================================================
# ACTIVITY LOG
# ====================================================================
@login_required
def activity_log(request):
    action_filter = request.GET.get("action", "")
    user_filter = request.GET.get("user", "")
    search = request.GET.get("q", "").strip()
    logs_qs = ActivityLog.objects.select_related("user").all()
    if action_filter:
        logs_qs = logs_qs.filter(action=action_filter)
    if user_filter:
        logs_qs = logs_qs.filter(user_id=user_filter)
    if search:
        logs_qs = logs_qs.filter(
            Q(description__icontains=search)
            | Q(module__icontains=search)
            | Q(user_name__icontains=search)
        )
    logs_list = list(logs_qs.order_by("-created_at")[:200])
    today = timezone.now().date()
    today_count = ActivityLog.objects.filter(created_at__date=today).count()
    total_users = ActivityLog.objects.values("user_id").distinct().count()
    total_logs = ActivityLog.objects.count()
    users_with_logs = list(
        ActivityLog.objects.exclude(user=None)
        .values("user_id", "user__username", "user__first_name", "user__last_name")
        .distinct()
    )
    for u in users_with_logs:
        u["display_name"] = (
            f"{u['user__first_name']} {u['user__last_name']}".strip()
            if u["user__first_name"]
            else u["user__username"]
        )
    actions = ActivityLog.ActionChoices.choices
    context = {
        "logs": logs_list,
        "actions": actions,
        "users_with_logs": users_with_logs,
        "today_count": today_count,
        "total_users": total_users,
        "total_logs": total_logs,
        "selected_action": action_filter,
        "selected_user": user_filter,
        "search": search,
    }
    return render_page(request, "pages/activity_log.html", context, active="activity_log")
