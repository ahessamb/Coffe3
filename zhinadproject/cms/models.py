from __future__ import annotations

from django.core.paginator import Paginator
from django.db import models
from django.utils import timezone

from wagtail import blocks
from wagtail.admin.panels import FieldPanel
from wagtail.fields import RichTextField, StreamField
from wagtail.images.blocks import ImageChooserBlock
from wagtail.models import Page


class HeadingBlock(blocks.StructBlock):
    text = blocks.CharBlock(required=True, label="عنوان")
    level = blocks.ChoiceBlock(
        choices=[
            ("h2", "H2"),
            ("h3", "H3"),
        ],
        default="h2",
        label="سطح عنوان",
    )

    class Meta:
        icon = "title"
        label = "عنوان"
        template = "cms/blocks/heading.html"


class ImageBlock(blocks.StructBlock):
    image = ImageChooserBlock(required=True, label="تصویر")
    caption = blocks.CharBlock(required=False, label="کپشن")
    alignment = blocks.ChoiceBlock(
        choices=[
            ("full", "تمام عرض"),
            ("left", "چپ"),
            ("right", "راست"),
        ],
        default="full",
        label="چیدمان",
    )

    class Meta:
        icon = "image"
        label = "تصویر"
        template = "cms/blocks/image.html"


class CalloutBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, label="عنوان")
    text = blocks.RichTextBlock(required=True, label="متن")

    class Meta:
        icon = "placeholder"
        label = "باکس تاکید"
        template = "cms/blocks/callout.html"


class DividerBlock(blocks.StaticBlock):
    class Meta:
        icon = "horizontalrule"
        label = "خط جداکننده"
        template = "cms/blocks/divider.html"


class ColumnsBlock(blocks.StructBlock):
    left = blocks.StreamBlock(
        [
            ("heading", HeadingBlock()),
            ("rich_text", blocks.RichTextBlock(label="متن")),
            ("image", ImageBlock()),
            ("callout", CalloutBlock()),
            ("divider", blocks.StaticBlock(icon="horizontalrule", label="خط جداکننده")),
        ],
        label="ستون چپ",
        required=False,
    )
    right = blocks.StreamBlock(
        [
            ("heading", HeadingBlock()),
            ("rich_text", blocks.RichTextBlock(label="متن")),
            ("image", ImageBlock()),
            ("callout", CalloutBlock()),
            ("divider", blocks.StaticBlock(icon="horizontalrule", label="خط جداکننده")),
        ],
        label="ستون راست",
        required=False,
    )

    class Meta:
        icon = "grip"
        label = "دو ستونه"
        template = "cms/blocks/columns.html"


class SectionBlock(blocks.StructBlock):
    title = blocks.CharBlock(required=False, label="عنوان بخش")
    body = blocks.StreamBlock(
        [
            ("heading", HeadingBlock()),
            ("rich_text", blocks.RichTextBlock(label="متن")),
            ("image", ImageBlock()),
            ("callout", CalloutBlock()),
            ("columns", ColumnsBlock()),
            ("divider", DividerBlock()),
            ("section", blocks.StructBlock(
                [
                    ("title", blocks.CharBlock(required=False, label="عنوان زیر‌بخش")),
                    ("body", blocks.StreamBlock(
                        [
                            ("heading", HeadingBlock()),
                            ("rich_text", blocks.RichTextBlock(label="متن")),
                            ("image", ImageBlock()),
                            ("callout", CalloutBlock()),
                            ("divider", DividerBlock()),
                        ],
                        label="محتوای زیر‌بخش",
                        required=False,
                    )),
                ],
                label="زیر‌بخش",
                icon="folder-open-inverse",
                template="cms/blocks/section_inner.html",
            )),
        ],
        label="محتوا",
        required=False,
    )

    class Meta:
        icon = "folder-open-1"
        label = "بخش"
        template = "cms/blocks/section.html"


BASE_STREAM_BLOCKS = [
    ("heading", HeadingBlock()),
    ("rich_text", blocks.RichTextBlock(label="متن")),
    ("image", ImageBlock()),
    ("callout", CalloutBlock()),
    ("columns", ColumnsBlock()),
    ("divider", DividerBlock()),
]


class AboutPage(Page):
    template = "cms/about_page.html"

    body = StreamField(BASE_STREAM_BLOCKS, use_json_field=True, blank=True, verbose_name="محتوا")

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "صفحه درباره ما"


class ContactPage(Page):
    template = "cms/contact_page.html"

    body = StreamField(
        [
            ("section", SectionBlock()),
            *BASE_STREAM_BLOCKS,
        ],
        use_json_field=True,
        blank=True,
        verbose_name="محتوا",
    )

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "صفحه تماس با ما"


class BlogIndexPage(Page):
    template = "cms/blog_index_page.html"
    subpage_types = ["cms.BlogPage"]

    intro = RichTextField(blank=True, verbose_name="متن معرفی")

    content_panels = Page.content_panels + [
        FieldPanel("intro"),
    ]

    class Meta:
        verbose_name = "صفحه لیست بلاگ"

    def get_context(self, request):
        context = super().get_context(request)
        posts = (
            BlogPage.objects.child_of(self)
            .live()
            .order_by("-published_at", "-first_published_at")
            .specific()
        )

        paginator = Paginator(posts, 9)
        page_number = request.GET.get("page")
        context["page_obj"] = paginator.get_page(page_number)
        context["blog_posts"] = context["page_obj"].object_list
        context["is_paginated"] = paginator.num_pages > 1
        return context


class BlogPage(Page):
    template = "cms/blog_page.html"
    parent_page_types = ["cms.BlogIndexPage"]

    excerpt = models.TextField(blank=True, verbose_name="خلاصه")
    author = models.CharField(max_length=100, blank=True, verbose_name="نویسنده")
    published_at = models.DateTimeField(default=timezone.now, verbose_name="تاریخ انتشار")
    views = models.IntegerField(default=0, verbose_name="تعداد بازدید")
    featured_image = models.ForeignKey(
        "wagtailimages.Image",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        verbose_name="تصویر شاخص (اختیاری)",
    )
    body = StreamField(BASE_STREAM_BLOCKS, use_json_field=True, blank=True, verbose_name="متن")

    content_panels = Page.content_panels + [
        FieldPanel("excerpt"),
        FieldPanel("author"),
        FieldPanel("published_at"),
        FieldPanel("featured_image"),
        FieldPanel("body"),
    ]

    class Meta:
        verbose_name = "پست بلاگ"


