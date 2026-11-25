#!/usr/bin/env python
"""
اسکریپت دانلود تصاویر محصولات از سایت wounda.ir
و ذخیره در پوشه static/img/products/

نحوه اجرا:
    cd django-crm
    python download_images.py
"""

import os
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMG_DIR = os.path.join(BASE_DIR, "static", "img", "products")

# Real image URLs from wounda.ir (extracted from shop page HTML)
PRODUCTS = [
    {
        "name": "پانسمان هیدروکل نازک هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-hydrocol-thin-300x300.webp",
        "local": "hydrocol_thin_hartmann.webp",
    },
    {
        "name": "پانسمان آلژینات سوربالگون هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-sorbalgon-300x300.webp",
        "local": "sorbalgon_hartmann.webp",
    },
    {
        "name": "پانسمان آلژینات کلسیم پرکننده سوربالگون هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-sorbalgon-filling-calcium-300x300.webp",
        "local": "sorbalgon_filling_hartmann.webp",
    },
    {
        "name": "پانسمان استریل درپ یددار یورودرم یوروفارم",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/uerofarm-euroderm-insize-incision-300x300.webp",
        "local": "euroderm_eurofarm.webp",
    },
    {
        "name": "پانسمان جراحی کاسموپور آنتی باکتریال هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-cosmopor-antibacterial-300x300.webp",
        "local": "cosmopor_antibac_hartmann.webp",
    },
    {
        "name": "پانسمان جراحی پددار کاسموپور هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-cosmopor-300x300.webp",
        "local": "cosmopor_hartmann.webp",
    },
    {
        "name": "پانسمان زتوویت پلاس سیلیکون بوردر هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-zetuvit-plus-silicone-border-300x300.webp",
        "local": "zetuvit_silicone_border_hartmann.webp",
    },
    {
        "name": "پانسمان زتوویت پلاس سیلیکونی هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-zetuvit-plus-silicone-300x300.webp",
        "local": "zetuvit_silicone_hartmann.webp",
    },
    {
        "name": "پانسمان شفاف رولی هیدروفیلم هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-hydrofilm-roll-300x300.webp",
        "local": "hydrofilm_roll_hartmann.webp",
    },
    {
        "name": "پانسمان شفاف هیدروفیلم پلاس هارتمن",
        "url": "https://wounda.ir/wp-content/uploads/2026/08/hartmann-hydrofilm-plus-300x300.webp",
        "local": "hydrofilm_plus_hartmann.webp",
    },
    {
        "name": "پانسمان طبابرن",
        "url": "https://wounda.ir/wp-content/uploads/2026/07/tababurn-burn-dressing-300x300.webp",
        "local": "tababurn.webp",
    },
    {
        "name": "پانسمان طبادرم",
        "url": "https://wounda.ir/wp-content/uploads/2026/07/tabaderm-hydrocolloid-dressing-300x300.webp",
        "local": "tabaderm.webp",
    },
    {
        "name": "پانسمان طبادرم پلاس نقره",
        "url": "https://wounda.ir/wp-content/uploads/2026/07/tabaderm-plus-silver-dressing-300x300.webp",
        "local": "tabaderm_silver.webp",
    },
    {
        "name": "پانسمان طبافلکس",
        "url": "https://wounda.ir/wp-content/uploads/2026/07/tabaflex-dressing-300x300.webp",
        "local": "tabaflex.webp",
    },
    {
        "name": "پانسمان طبافلکس پرو",
        "url": "https://wounda.ir/wp-content/uploads/2026/07/tebaflex-pro-dressing-300x300.webp",
        "local": "tabaflex_pro.webp",
    },
]


def download_image(url, filepath):
    """Download an image from URL to filepath."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            data = response.read()
            if len(data) < 100:
                return False, "Image too small"
            with open(filepath, "wb") as f:
                f.write(data)
            return True, f"{len(data)} bytes"
    except urllib.error.HTTPError as e:
        return False, f"HTTP {e.code}"
    except Exception as e:
        return False, str(e)


def main():
    os.makedirs(IMG_DIR, exist_ok=True)

    print("=" * 60)
    print("  📥 دانلود تصاویر محصولات از wounda.ir")
    print("=" * 60)
    print(f"\n  پوشه ذخیره: {IMG_DIR}\n")

    success = 0
    failed = 0

    for product in PRODUCTS:
        name = product["name"]
        url = product["url"]
        local = product["local"]
        filepath = os.path.join(IMG_DIR, local)

        if os.path.exists(filepath) and os.path.getsize(filepath) > 100:
            print(f"  ✓ {name} — از قبل موجود")
            success += 1
            continue

        print(f"  ⏳ دانلود: {name}...", end=" ", flush=True)
        ok, detail = download_image(url, filepath)
        if ok:
            print(f"✓ ({detail})")
            success += 1
        else:
            print(f"✗ ({detail})")
            failed += 1

    print(f"\n  {'─' * 54}")
    print(f"  ✓ موفق: {success}")
    print(f"  ✗ ناموفق: {failed}")

    if failed > 0:
        print(f"\n  ⚠️  برخی تصاویر دانلود نشدند. این طبیعی است اگر:")
        print(f"     - سایت wounda.ir در دسترس نباشد")
        print(f"     - URL تصاویر تغییر کرده باشد")
        print(f"\n  💡 در این صورت، از اموجی‌های موجود استفاده می‌شود.")

    print(f"\n  {'=' * 54}\n")


if __name__ == "__main__":
    main()
