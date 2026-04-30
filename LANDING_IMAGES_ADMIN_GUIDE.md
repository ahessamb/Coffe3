# Landing images (Logo / Hero album / Footer) — Admin Guide

This project now supports **optional, admin-configurable landing images**:

- **Logo image** (replaces the default logo if set)
- **Hero album** (multiple images on the home page hero, with ordering + optional slideshow)
- **Footer background image** (large decorative image inside the footer)

If you **do not** set any of these images, the website keeps the **current default** look.

---

## Where to configure (Django admin)

Go to:

- **Admin → تنظیمات سایت** (`SiteSettings`)

> Notes
> - There is only **one** `SiteSettings` record (the admin UI prevents adding more than one).
> - Hero album images are managed as an inline list inside the same page.

---

## 1) Set the logo image (optional)

In **`SiteSettings`**:

- Upload **`لوگوی سایت (اختیاری)`** (`logo_image`)

### Result
- Header logo (`img.logo-image`) will use your uploaded image.
- If empty, it falls back to the default static file: `static/website/images/logo.png`.

---

## 2) Set the footer background image (optional)

In **`SiteSettings`**:

- Upload **`تصویر پس‌زمینه فوتر (اختیاری)`** (`footer_image`)

### Result
- The image is rendered inside `footer.footer` using CSS `::before`.
- Placement/size is fixed to match your requested geometry:
  - `top: 135px; left: 0px; width: 790px; height: 577px;`
- If empty, footer remains unchanged (no background image).

---

## 3) Set the home hero album (multiple images, optional)

In **`SiteSettings`**, find the inline section:

- **تصاویر هدر صفحه اصلی** (`HomeHeroImage`)

For each row:

- **تصویر**: upload an image
- **ترتیب** (`order`): lower numbers appear first
- **فعال** (`is_active`): only active images are shown

### Result
- Images are rendered behind the hero content on the home page.
- Placement/size is fixed to match your requested geometry:
  - `top: 98px; left: 0px; width: 489px; height: 429px;`
- If there are **2+ active images**, the page automatically fades between them (slideshow).
- If there are **0 active images**, hero renders exactly like before (no album).

---

## Technical reference (files)

- **Models**: `zhinadproject/website/models.py`
  - `SiteSettings.logo_image`
  - `SiteSettings.footer_image`
  - `HomeHeroImage` model
- **Admin UI**: `zhinadproject/website/admin.py`
  - `HomeHeroImage` inline in `SiteSettingsAdmin`
- **Global template context**: `zhinadproject/website/context_processors.py`
  - `site_settings`, `home_hero_images`
- **Templates**:
  - `zhinadproject/website/templates/website/base.html` (logo + footer background)
  - `zhinadproject/website/templates/website/home.html` (hero album)
- **CSS**: `zhinadproject/website/static/website/css/style.css`

