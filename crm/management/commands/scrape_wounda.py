"""
Management command to scrape products from wounda.ir and save them
into the Product (and Brand) models, keeping images ONLINE via URL.

Usage examples:
    # فقط URL تصاویر ذخیره شود (پیش‌فرض - تصاویر آنلاین)
    python manage.py scrape_wounda --url https://wounda.ir/shop/

    # استفاده از پروکسی برای دور زدن hotlink protection
    python manage.py scrape_wounda --url https://wounda.ir/shop/ --proxy-images

    # دانلود تصاویر در ImageField (لوکال)
    python manage.py scrape_wounda --url https://wounda.ir/shop/ --download-images

    # فقط تست بدون ذخیره در دیتابیس
    python manage.py scrape_wounda --url https://wounda.ir/shop/ --dry-run
"""

import os
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from crm.models import Brand, Product


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "fa-IR,fa;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

# سرویس پروکسی تصویر برای دور زدن hotlink protection
IMAGE_PROXY_BASE = "https://images.weserv.nl/?url="


class Command(BaseCommand):
    help = "Scrape products from wounda.ir and save them to the database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--url",
            type=str,
            default="https://wounda.ir/",
            help="The shop listing URL to start scraping from.",
        )
        parser.add_argument(
            "--delay",
            type=float,
            default=1.0,
            help="Delay between requests in seconds (default: 1.0).",
        )
        parser.add_argument(
            "--max-pages",
            type=int,
            default=10,
            help="Maximum number of listing pages to crawl (default: 10).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and print results without saving to database.",
        )
        parser.add_argument(
            "--proxy-images",
            action="store_true",
            help="Store image URLs via images.weserv.nl proxy to bypass hotlinking.",
        )
        parser.add_argument(
            "--download-images",
            action="store_true",
            help="Download images into Product.image (ImageField).",
        )

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------
    def handle(self, *args, **options):
        self.base_url = options["url"]
        self.delay = options["delay"]
        self.max_pages = options["max_pages"]
        self.dry_run = options["dry_run"]
        self.proxy_images = options["proxy_images"]
        self.download_images = options["download_images"]

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN mode: nothing will be saved."))

        session = requests.Session()
        session.headers.update(DEFAULT_HEADERS)

        urls_to_visit = [self.base_url]
        visited = set()
        page_count = 0

        created_count = 0
        updated_count = 0
        failed_count = 0

        while urls_to_visit and page_count < self.max_pages:
            url = urls_to_visit.pop(0)
            if url in visited:
                continue
            visited.add(url)
            page_count += 1

            self.stdout.write(f"[{page_count}] Fetching: {url}")
            try:
                response = session.get(url, timeout=30)
                response.raise_for_status()
            except requests.RequestException as e:
                self.stdout.write(self.style.WARNING(f"  Failed to fetch: {e}"))
                continue

            soup = BeautifulSoup(response.text, "html.parser")

            # ----------------------------------------------------------
            # ⚠️ سلکتور کارت محصول - باید با ساختار واقعی سایت تنظیم شود
            # ----------------------------------------------------------
            product_cards = soup.select(
                ".product-item, .product, li.product, "
                ".woocommerce-loop-product__link, article.product"
            )

            self.stdout.write(f"  Found {len(product_cards)} product cards")

            for card in product_cards:
                try:
                    result = self._process_card(card, url, session)
                    if result == "created":
                        created_count += 1
                    elif result == "updated":
                        updated_count += 1
                except Exception as e:
                    failed_count += 1
                    self.stdout.write(self.style.WARNING(f"  Skipped a product: {e}"))

            # پیدا کردن لینک صفحه بعدی
            next_url = self._find_next_page(soup, url)
            if next_url and next_url not in visited:
                urls_to_visit.append(next_url)

            time.sleep(self.delay)

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. Pages: {page_count}, Created: {created_count}, "
            f"Updated: {updated_count}, Failed: {failed_count}"
        ))

    # ------------------------------------------------------------------
    # Process a single product card
    # ------------------------------------------------------------------
    def _process_card(self, card, page_url, session):
        # --- نام محصول ---
        name = self._extract_text(
            card,
            [
                ".woocommerce-loop-product__title",
                ".product-title",
                "h2",
                "h3",
                ".title",
            ],
        )
        if not name:
            return None
        name = name.strip()

        # --- قیمت ---
        price_text = self._extract_text(
            card,
            [".price", ".amount", ".woocommerce-Price-amount", ".product-price"],
        )
        price = self._parse_price(price_text)

        # --- برند ---
        brand_name = self._extract_text(
            card, [".brand", ".product-brand", ".manufacturer"]
        )

        # --- تصویر (با پشتیبانی از lazy-load) ---
        image_src = (
            self._extract_attr(card, "img", "src")
            or self._extract_attr(card, "img", "data-src")
            or self._extract_attr(card, "img", "data-lazy-src")
            or self._extract_attr(card, "img", "data-original")
        )
        image_url = urljoin(page_url, image_src) if image_src else ""

        # اعمال پروکسی در صورت درخواست
        if image_url and self.proxy_images:
            image_url = IMAGE_PROXY_BASE + image_url

        # --- دسته‌بندی و نوع زخم بر اساس نام ---
        category = self._guess_category(name)
        wound_type = self._guess_wound_type(name)

        # --- توضیحات ---
        description = self._extract_text(
            card, [".description", ".product-description", "p"]
        ) or ""

        # چاپ در حالت dry-run
        if self.dry_run:
            self.stdout.write(
                f"  → {name} | price={price} | cat={category} | "
                f"wound={wound_type} | img={image_url[:80]}"
            )
            return None

        # --- برند: ساخت یا دریافت ---
        brand = None
        if brand_name:
            brand, _ = Brand.objects.get_or_create(
                name=brand_name.strip(),
                defaults={"logo_emoji": "🏷️"},
            )
        if brand is None:
            brand, _ = Brand.objects.get_or_create(
                name="نامشخص",
                defaults={"logo_emoji": "❓", "description": "برند نامشخص"},
            )

        # --- ایجاد یا بروزرسانی محصول ---
        with transaction.atomic():
            product, created = Product.objects.update_or_create(
                name=name,
                defaults={
                    "brand": brand,
                    "category": category,
                    "wound_type": wound_type,
                    "description": description,
                    "price": price,
                    "image_url": image_url,
                    "is_active": True,
                },
            )

            # دانلود اختیاری تصویر در ImageField
            if self.download_images and image_url and not product.image:
                self._download_image(product, image_url, session)

        return "created" if created else "updated"

    # ------------------------------------------------------------------
    # Download image into ImageField
    # ------------------------------------------------------------------
    def _download_image(self, product, image_url, session):
        try:
            # اگر پروکسی فعال است، برای دانلود از URL اصلی استفاده کن
            download_url = image_url
            if self.proxy_images and image_url.startswith(IMAGE_PROXY_BASE):
                download_url = image_url[len(IMAGE_PROXY_BASE):]

            resp = session.get(download_url, timeout=30)
            resp.raise_for_status()

            # تشخیص پسوند از content-type
            content_type = resp.headers.get("Content-Type", "image/jpeg")
            ext = "jpg"
            if "png" in content_type:
                ext = "png"
            elif "webp" in content_type:
                ext = "webp"
            elif "gif" in content_type:
                ext = "gif"

            safe_name = f"product_{product.pk}.{ext}"
            product.image.save(safe_name, ContentFile(resp.content), save=True)
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"  Could not download image for {product.pk}: {e}")
            )

    # ------------------------------------------------------------------
    # Find next page link
    # ------------------------------------------------------------------
    def _find_next_page(self, soup, current_url):
        selectors = [
            "a.next.page-numbers",
            "a.next",
            "link[rel='next']",
            ".pagination a.next",
        ]
        for sel in selectors:
            el = soup.select_one(sel)
            if el:
                href = el.get("href")
                if href:
                    return urljoin(current_url, href)
        return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _extract_text(self, parent, selectors):
        for sel in selectors:
            el = parent.select_one(sel)
            if el:
                text = el.get_text(strip=True)
                if text:
                    return text
        return None

    def _extract_attr(self, parent, tag, attr):
        el = parent.select_one(tag)
        if el:
            return el.get(attr, "")
        return ""

    def _parse_price(self, text):
        if not text:
            return 0
        # تبدیل ارقام فارسی/عربی به انگلیسی
        translation = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        text = text.translate(translation)
        digits = "".join(c for c in text if c.isdigit())
        try:
            return int(digits) if digits else 0
        except ValueError:
            return 0

    def _guess_category(self, name):
        mapping = {
            "هیدروکلوئید": "hydrocolloid",
            "هیدروکل": "hydrocolloid",
            "فوم": "foam",
            "آلژینات": "alginate",
            "نقره": "silver",
            "هیدروژل": "hydrogel",
            "هیدروفایبر": "hydrofiber",
            "کلاژن": "collagen",
            "عسل": "honey",
            "جاذب": "absorbent",
            "جراحی": "surgical",
            "شفاف": "transparent",
            "ساکرال": "sacral",
            "وکیوم": "npwt",
            "پاشنه": "heel",
            "تراکئوستومی": "tracheostomy",
            "دبرید": "debridement",
            "ترمیم": "healing",
            "چسب": "adhesive",
            "کانکیو": "concave",
        }
        for keyword, category in mapping.items():
            if keyword in name:
                return category
        return "other"

    def _guess_wound_type(self, name):
        mapping = {
            "دیابتی": "diabetic",
            "بستر": "pressure",
            "وریدی": "venous",
            "شریانی": "arterial",
            "جراحی": "surgical",
            "سوختگی": "burn",
            "تروماتیک": "trauma",
            "مزمن": "chronic",
            "حاد": "acute",
        }
        for keyword, wtype in mapping.items():
            if keyword in name:
                return wtype
        return "all"