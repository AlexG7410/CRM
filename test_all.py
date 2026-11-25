#!/usr/bin/env python
"""
=====================================================
  ابزار تست کامل سامانه CRM متخصص کلینیک زخم
  Wound Care CRM - Full Test Suite
=====================================================

نحوه اجرا:
    cd django-crm
    source venv/bin/activate
    python test_all.py

یا با سرور در حال اجرا:
    python test_all.py --host 127.0.0.1 --port 8000
"""

import sys
import os
import json
import time
import argparse
import requests

# Colors for terminal output
class C:
    HEADER    = '\033[95m'
    BLUE      = '\033[94m'
    CYAN      = '\033[96m'
    GREEN     = '\033[92m'
    YELLOW    = '\033[93m'
    RED       = '\033[91m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
    END       = '\033[0m'
    GRAY      = '\033[90m'

# =====================================================
# Test Result Tracker
# =====================================================
class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = []
        self.results = []

    def record(self, name, status, detail=""):
        self.results.append({
            "name": name,
            "status": status,
            "detail": detail,
        })
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
            self.errors.append(f"{name}: {detail}")
        else:
            self.skipped += 1

    def summary(self):
        total = self.passed + self.failed + self.skipped
        return {
            "total": total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }


# =====================================================
# CRM Test Suite
# =====================================================
class CRMTestSuite:
    def __init__(self, host="127.0.0.1", port=8000):
        self.base_url = f"http://{host}:{port}"
        self.session = requests.Session()
        self.results = TestResults()
        self.csrf_token = None

    def log(self, msg, color=C.END):
        print(f"{color}{msg}{C.END}")

    def line(self, char="─", length=60, color=C.GRAY):
        self.log(char * length, color)

    # -------------------------------------------------
    # Helpers
    # -------------------------------------------------
    def login(self, username="admin", password="admin123"):
        """Login and store session cookies."""
        try:
            resp = self.session.get(f"{self.base_url}/login/", timeout=10)
            if resp.status_code != 200:
                return False

            # Extract CSRF token
            import re
            match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', resp.text)
            if not match:
                return False
            csrf = match.group(1)

            # Submit login
            resp = self.session.post(
                f"{self.base_url}/login/",
                data={
                    "csrfmiddlewaretoken": csrf,
                    "username": username,
                    "password": password,
                    "next": "/",
                },
                headers={"Referer": f"{self.base_url}/login/"},
                timeout=10,
                allow_redirects=False,
            )
            return resp.status_code == 302
        except Exception as e:
            print(f"Login error: {e}")
            return False

    def get_csrf(self, path):
        """Get CSRF token from a form page."""
        try:
            resp = self.session.get(f"{self.base_url}{path}", timeout=10)
            if resp.status_code != 200:
                return None
            import re
            match = re.search(r'csrfmiddlewaretoken" value="([^"]+)"', resp.text)
            return match.group(1) if match else None
        except:
            return None

    def test_get(self, name, path, expected_status=200):
        """Test a GET request."""
        try:
            resp = self.session.get(f"{self.base_url}{path}", timeout=10, allow_redirects=True)
            status = resp.status_code
            if status == expected_status:
                self.results.record(name, "PASS", f"HTTP {status}")
                self.log(f"  ✓ {name}", C.GREEN)
            else:
                self.results.record(name, "FAIL", f"HTTP {status} (expected {expected_status})")
                self.log(f"  ✗ {name} — HTTP {status} (expected {expected_status})", C.RED)
            return resp
        except Exception as e:
            self.results.record(name, "FAIL", str(e))
            self.log(f"  ✗ {name} — Error: {e}", C.RED)
            return None

    def test_post(self, name, path, data, expected_status=302):
        """Test a POST request with CSRF."""
        try:
            csrf = self.get_csrf(path)
            if not csrf:
                # Try without getting CSRF (some endpoints don't have forms)
                csrf = ""
            post_data = dict(data)
            if csrf:
                post_data["csrfmiddlewaretoken"] = csrf

            resp = self.session.post(
                f"{self.base_url}{path}",
                data=post_data,
                headers={"Referer": f"{self.base_url}{path}"},
                timeout=10,
                allow_redirects=False,
            )
            status = resp.status_code
            if status == expected_status:
                self.results.record(name, "PASS", f"HTTP {status}")
                self.log(f"  ✓ {name}", C.GREEN)
            else:
                self.results.record(name, "FAIL", f"HTTP {status} (expected {expected_status})")
                self.log(f"  ✗ {name} — HTTP {status} (expected {expected_status})", C.RED)
            return resp
        except Exception as e:
            self.results.record(name, "FAIL", str(e))
            self.log(f"  ✗ {name} — Error: {e}", C.RED)
            return None

    def test_download(self, name, path, expected_content_type="text/csv"):
        """Test a file download endpoint."""
        try:
            resp = self.session.get(f"{self.base_url}{path}", timeout=10, allow_redirects=True)
            ct = resp.headers.get("Content-Type", "")
            if resp.status_code == 200 and expected_content_type in ct:
                size = len(resp.content)
                self.results.record(name, "PASS", f"HTTP {resp.status_code}, {size} bytes")
                self.log(f"  ✓ {name} — {size} bytes", C.GREEN)
            else:
                self.results.record(name, "FAIL", f"HTTP {resp.status_code}, CT: {ct}")
                self.log(f"  ✗ {name} — HTTP {resp.status_code}, CT: {ct}", C.RED)
            return resp
        except Exception as e:
            self.results.record(name, "FAIL", str(e))
            self.log(f"  ✗ {name} — Error: {e}", C.RED)
            return None

    # -------------------------------------------------
    # Test Sections
    # -------------------------------------------------
    def test_auth(self):
        """Test authentication."""
        self.log("\n🔐 احراز هویت (Authentication)", C.BOLD + C.CYAN)
        self.line()

        # Test login page accessible
        self.test_get("صفحه ورود نمایش داده می‌شود", "/login/", 200)

        # Test wrong login
        resp = self.test_post(
            "ورود با گذرواژه اشتباه رد می‌شود",
            "/login/",
            {"username": "admin", "password": "wrongpass"},
            expected_status=200,  # stays on login page
        )

        # Test correct login
        if self.login():
            self.results.record("ورود صحیح موفق است", "PASS")
            self.log("  ✓ ورود صحیح موفق است", C.GREEN)
        else:
            self.results.record("ورود صحیح موفق است", "FAIL", "Login failed")
            self.log("  ✗ ورود صحیح موفق است", C.RED)

        # Test logout
        resp = self.test_get("خروج از سیستم", "/logout/", 302)

        # Re-login for remaining tests
        self.login()

    def test_dashboard(self):
        """Test dashboard."""
        self.log("\n📊 داشبورد", C.BOLD + C.CYAN)
        self.line()
        self.test_get("داشبورد اصلی", "/", 200)

    def test_customers(self):
        """Test customers section."""
        self.log("\n👥 مشتریان", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست مشتریان", "/customers/", 200)
        self.test_get("افزودن مشتری (فرم)", "/customers/add/", 200)

        # Find the first real customer ID from the list page
        cust_id = None
        try:
            resp = self.session.get(f"{self.base_url}/customers/", timeout=10)
            import re
            matches = re.findall(r'/customers/(\d+)/', resp.text)
            if matches:
                cust_id = matches[0]
        except:
            pass

        if cust_id:
            self.test_get(f"جزئیات مشتری (ID={cust_id})", f"/customers/{cust_id}/", 200)
        else:
            self.results.record("جزئیات مشتری", "SKIP", "هیچ مشتری‌ای در دیتابیس وجود ندارد")
            self.log("  ⊘ جزئیات مشتری — رد شد (مشتری‌ای وجود ندارد)", C.YELLOW)

        self.test_download("خروجی اکسل مشتریان", "/customers/export/excel/")

        # Test add customer POST
        self.test_post(
            "ثبت مشتری جدید",
            "/customers/add/",
            {
                "name": "تست مشتری سیستمی",
                "type": "wound_specialist",
                "phone": "09120000000",
                "city": "تهران",
                "workplace": "کلینیک تست",
                "commission_rate": "20.00",
                "status": "active",
            },
        )

    def test_products(self):
        """Test products section."""
        self.log("\n📦 محصولات", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست محصولات", "/products/", 200)
        self.test_get("افزودن محصول (فرم)", "/products/add/", 200)
        self.test_get("افزودن برند (فرم)", "/brands/add/", 200)

        # Test filter
        self.test_get("فیلتر برند", "/products/?brand=1", 200)
        self.test_get("جستجوی محصول", "/products/?q=پانسمان", 200)
        self.test_get("فیلتر نوع زخم", "/products/?wound_type=diabetic", 200)

        # Test add product POST
        self.test_post(
            "ثبت محصول جدید",
            "/products/add/",
            {
                "brand": "1",
                "name": "محصول تست سیستمی",
                "category": "foam",
                "wound_type": "all",
                "price": "100000",
                "stock": "50",
                "unit": "عدد",
                "low_stock_threshold": "10",
            },
        )

    def test_consultation(self):
        """Test online consultation."""
        self.log("\n💬 مشاوره آنلاین", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست مشاوره‌ها", "/consultation/", 200)
        self.test_get("فرم ثبت مشاوره", "/consultation/add/", 200)

        # Test add consultation
        self.test_post(
            "ثبت مشاوره جدید",
            "/consultation/add/",
            {
                "customer_name": "بیمار تست",
                "phone": "09121111111",
                "wound_type": "diabetic",
                "question": "زخم پای دیابتی دارم چه کنم؟",
            },
        )

    def test_satisfaction(self):
        """Test satisfaction reviews."""
        self.log("\n⭐ رضایت‌مندی", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست نظرات", "/satisfaction/", 200)
        self.test_get("فرم ثبت نظر", "/satisfaction/add/", 200)

        self.test_post(
            "ثبت نظر جدید",
            "/satisfaction/add/",
            {
                "customer": "1",
                "rating": "5",
                "product_quality": "5",
                "service_quality": "4",
                "delivery_speed": "5",
                "comment": "بسیار عالی",
            },
        )

    def test_inventory(self):
        """Test inventory."""
        self.log("\n🏥 موجودی انبار + قیمت", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست موجودی انبار", "/inventory/", 200)

    def test_warehouse(self):
        """Test warehouse movements."""
        self.log("\n📥 انبار و خروجی", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست تراکنش‌های انبار", "/warehouse/", 200)
        self.test_get("فرم ثبت تراکنش", "/warehouse/add/", 200)

        # Test IN
        self.test_post(
            "ثبت تراکنش ورودی",
            "/warehouse/add/",
            {
                "product": "1",
                "type": "in",
                "quantity": "50",
                "reason": "purchase",
                "operator": "تست سیستمی",
                "reference": "فاکتور تست",
            },
        )

        # Test OUT
        self.test_post(
            "ثبت تراکنش خروجی",
            "/warehouse/add/",
            {
                "product": "1",
                "type": "out",
                "quantity": "10",
                "reason": "order_delivery",
                "operator": "تست سیستمی",
            },
        )

    def test_invoices(self):
        """Test invoices."""
        self.log("\n📄 فاکتور", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست فاکتورها", "/invoices/", 200)
        self.test_get("فرم صدور فاکتور", "/invoices/add/", 200)

    def test_payments(self):
        """Test payments."""
        self.log("\n💳 پرداخت", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست پرداخت‌ها", "/payments/", 200)
        self.test_get("فرم ثبت پرداخت", "/payments/add/", 200)

    def test_commissions(self):
        """Test commissions."""
        self.log("\n💰 پورسانت مشتریان", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست پورسانت‌ها", "/commissions/", 200)

    def test_sales_report(self):
        """Test sales report."""
        self.log("\n📈 گزارش فروش بازاریابی", C.BOLD + C.CYAN)
        self.line()
        self.test_get("گزارش فروش", "/sales-report/", 200)
        self.test_download("خروجی اکسل فروش", "/sales-report/export/excel/")

    def test_product_request(self):
        """Test product request."""
        self.log("\n📋 فرم درخواست محصول", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لیست درخواست‌ها", "/product-request/", 200)
        self.test_get("فرم درخواست جدید", "/product-request/add/", 200)

        # Test add
        self.test_post(
            "ثبت درخواست محصول",
            "/product-request/add/",
            {
                "customer": "2",
                "product_name": "پانسمان تست سیستمی",
                "quantity": "30",
                "unit": "عدد",
                "notes": "فوری",
            },
        )

    def test_procurement(self):
        """Test procurement."""
        self.log("\n📤 تدارکات", C.BOLD + C.CYAN)
        self.line()
        self.test_get("صفحه تدارکات", "/procurement/", 200)

    def test_orders(self):
        """Test orders."""
        self.log("\n🛒 سفارشات", C.BOLD + C.CYAN)
        self.line()
        self.test_get("فرم ثبت سفارش", "/customer-order/", 200)
        self.test_get("لیست سفارش‌ها", "/orders/", 200)

    def test_financial_tracking(self):
        """Test financial tracking."""
        self.log("\n📊 پیگیری مالی", C.BOLD + C.CYAN)
        self.line()
        self.test_get("پیگیری مالی", "/financial-tracking/", 200)

    def test_daily_report(self):
        """Test daily report."""
        self.log("\n📝 گزارش روزانه پرزنت", C.BOLD + C.CYAN)
        self.line()
        self.test_get("گزارش روزانه", "/daily-report/", 200)

    def test_activity_log(self):
        """Test activity log."""
        self.log("\n🔍 لاگ فعالیت‌ها", C.BOLD + C.CYAN)
        self.line()
        self.test_get("لاگ فعالیت‌ها", "/activity-log/", 200)

    def test_admin(self):
        """Test Django admin."""
        self.log("\n⚙️ پنل ادمین", C.BOLD + C.CYAN)
        self.line()
        self.test_get("پنل ادمین", "/admin/", 200)

    # -------------------------------------------------
    # Run All Tests
    # -------------------------------------------------
    def run_all(self):
        """Run all test sections."""
        start_time = time.time()

        self.log("\n" + "=" * 60, C.BOLD + C.TEAL if hasattr(C, 'TEAL') else C.BOLD + C.CYAN)
        self.log("  🧪 ابزار تست کامل سامانه CRM متخصص کلینیک زخم", C.BOLD + C.CYAN)
        self.log("  Wound Care CRM - Full Test Suite", C.BOLD + C.CYAN)
        self.log("=" * 60, C.BOLD + C.CYAN)
        self.log(f"\n  سرور: {self.base_url}", C.GRAY)
        self.log(f"  زمان شروع: {time.strftime('%Y/%m/%d %H:%M:%S')}\n", C.GRAY)

        # Login first
        self.log("🔐 در حال ورود به سیستم...", C.YELLOW)
        if not self.login():
            self.log("❌ ورود ناموفق! آیا سرور اجرا شده و کاربر admin/admin123 وجود دارد؟", C.RED)
            self.log("\nبرای ساخت کاربر ادمین اجرا کنید:", C.YELLOW)
            self.log("  python manage.py createsuperuser", C.GRAY)
            return
        self.log("✓ ورود موفق\n", C.GREEN)

        # Run each test section
        self.test_dashboard()
        self.test_customers()
        self.test_products()
        self.test_consultation()
        self.test_satisfaction()
        self.test_inventory()
        self.test_warehouse()
        self.test_invoices()
        self.test_payments()
        self.test_commissions()
        self.test_sales_report()
        self.test_product_request()
        self.test_procurement()
        self.test_orders()
        self.test_financial_tracking()
        self.test_daily_report()
        self.test_activity_log()
        self.test_admin()

        # Summary
        elapsed = time.time() - start_time
        self.print_summary(elapsed)

    def print_summary(self, elapsed):
        """Print test summary."""
        s = self.results.summary()

        self.log("\n" + "=" * 60, C.BOLD)
        self.log("  📋 خلاصه نتایج تست", C.BOLD + C.CYAN)
        self.log("=" * 60, C.BOLD)

        # Stats
        self.log(f"\n  کل تست‌ها:     {s['total']}", C.BOLD)
        self.log(f"  ✓ موفق:        {s['passed']}", C.GREEN + C.BOLD if s['passed'] else C.GREEN)
        self.log(f"  ✗ ناموفق:      {s['failed']}", C.RED + C.BOLD if s['failed'] else C.RED)
        self.log(f"  ⊘ رد شده:      {s['skipped']}", C.YELLOW)
        self.log(f"  ⏱ زمان کل:     {elapsed:.1f} ثانیه", C.GRAY)

        # Pass rate
        if s['total'] > 0:
            rate = (s['passed'] / s['total']) * 100
            color = C.GREEN if rate >= 90 else C.YELLOW if rate >= 70 else C.RED
            self.log(f"\n  نرخ موفقیت:    {rate:.1f}%", color + C.BOLD)

        # Errors
        if self.results.errors:
            self.log(f"\n  {'─' * 54}", C.GRAY)
            self.log("  ❌ خطاهای پیدا شده:", C.RED + C.BOLD)
            for err in self.results.errors:
                self.log(f"    • {err}", C.RED)

        # Final status
        self.log(f"\n  {'─' * 54}", C.GRAY)
        if s['failed'] == 0:
            self.log("  ✅ همه تست‌ها موفق بودند!", C.GREEN + C.BOLD)
        else:
            self.log(f"  ⚠️  {s['failed']} تست ناموفق داشت.", C.YELLOW + C.BOLD)

        self.log("\n" + "=" * 60 + "\n", C.BOLD)


# =====================================================
# Main
# =====================================================
def check_django_setup():
    """Check if Django is set up."""
    try:
        import django
        return True
    except ImportError:
        return False


def main():
    parser = argparse.ArgumentParser(
        description="ابزار تست کامل سامانه CRM متخصص کلینیک زخم",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
نحوه اجرا:

  1. ابتدا سرور را اجرا کنید:
     python manage.py runserver

  2. سپس این اسکریپت را اجرا کنید:
     python test_all.py

  یا با تنظیمات سفارشی:
     python test_all.py --host 127.0.0.1 --port 8000 --username admin --password admin123
        """,
    )
    parser.add_argument("--host", default="127.0.0.1", help="آدرس سرور (پیش‌فرض: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="پورت سرور (پیش‌فرض: 8000)")
    parser.add_argument("--username", default="admin", help="نام کاربری (پیش‌فرض: admin)")
    parser.add_argument("--password", default="admin123", help="گذرواژه (پیش‌فرض: admin123)")

    args = parser.parse_args()

    # Check if requests is installed
    try:
        import requests
    except ImportError:
        print(f"{C.RED}❌ کتابخانه requests نصب نشده است.{C.END}")
        print(f"{C.YELLOW}نصب کنید: pip install requests{C.END}")
        sys.exit(1)

    # Check if server is running
    suite = CRMTestSuite(args.host, args.port)
    try:
        resp = requests.get(f"{suite.base_url}/login/", timeout=3)
    except requests.ConnectionError:
        print(f"{C.RED}❌ سرور در {suite.base_url} اجرا نشده است!{C.END}")
        print(f"\n{C.YELLOW}ابتدا سرور را اجرا کنید:{C.END}")
        print(f"  {C.GRAY}python manage.py runserver{C.END}")
        sys.exit(1)

    # Run tests
    suite.run_all()


if __name__ == "__main__":
    main()
