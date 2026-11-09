# -*- coding: utf-8 -*-
"""
يبني سيرة ذاتية من صفحة واحدة بنفس تصميم ملف «سيف البتول-السيرة الذاتية-1.pdf»،
مع تغيير الاسم إلى «مجد الشاهري»، واستبدال الصورة بالصورة المرفقة،
ودمج معلومات ملف «انشا ملف مجد.pdf» مع محتوى السيرة الأصلي في الصفحة الأولى.

المخرجات:
  مجد الشاهري-السيرة الذاتية.pdf
  مجد الشاهري-السيرة الذاتية.png  (معاينة)
"""

from __future__ import annotations

import html as html_lib
import io
import json
import os
import re
import tarfile
import urllib.request

import pymupdf as fitz
from PIL import Image, ImageDraw, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
SRC_CV = os.path.join(ROOT, "سيف البتول-السيرة الذاتية-1.pdf")
SRC_PHOTO = os.path.join(ROOT, "IMG-20261026-WA0001.jpg")
OUT_PDF = os.path.join(ROOT, "مجد الشاهري-السيرة الذاتية.pdf")
OUT_PNG = os.path.join(ROOT, "مجد الشاهري-السيرة الذاتية.png")
OUT_TXT = os.path.join(ROOT, "مجد الشاهري-السيرة الذاتية.txt")

W, H = 595.276, 892.457          # مقاس صفحة السيرة الأصلية بالـ pt
S = 3                            # دقة الخلفية: 3 بكسل لكل نقطة
RIGHT_X = 375                    # بداية العمود الأيمن
NAVY = (22, 44, 74)
TITLE = (15, 38, 86)
SIDEBAR = (247, 248, 250)
GRAY = (213, 219, 227)
BODY = (36, 49, 61)
MUTED = (92, 108, 124)

FONTS = [
    "cairo-arabic-400-normal.ttf",
    "cairo-arabic-700-normal.ttf",
    "cairo-latin-400-normal.ttf",
    "cairo-latin-700-normal.ttf",
]


def ensure_fonts() -> None:
    """ينزّل خطوط Cairo (من حزمة npm الرسمية) ويحوّلها إلى TTF عند الحاجة."""
    if all(os.path.exists(os.path.join(FONT_DIR, f)) for f in FONTS):
        return
    os.makedirs(FONT_DIR, exist_ok=True)
    from fontTools.ttLib import TTFont

    meta = json.load(urllib.request.urlopen(
        "https://registry.npmjs.org/@fontsource/cairo/latest", timeout=30))
    raw = urllib.request.urlopen(meta["dist"]["tarball"], timeout=60).read()
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        for member in tf.getnames():
            base = os.path.basename(member)
            ttf_name = base.replace(".woff2", ".ttf")
            if ttf_name in FONTS:
                font = TTFont(io.BytesIO(tf.extractfile(member).read()))
                font.flavor = None
                font.save(os.path.join(FONT_DIR, ttf_name))


BASE_CSS = """
@font-face {font-family: cairo; src: url(cairo-arabic-400-normal.ttf); font-weight: 400;}
@font-face {font-family: cairo; src: url(cairo-arabic-700-normal.ttf); font-weight: 700;}
@font-face {font-family: cl;    src: url(cairo-latin-400-normal.ttf);  font-weight: 400;}
@font-face {font-family: cl;    src: url(cairo-latin-700-normal.ttf);  font-weight: 700;}
body {font-family: cairo, cl; margin:0; padding:0; color:#24313d; font-size:9pt;}
/* ملاحظة: محرك HTML في MuPDF يعكس معنى text-align مع direction:rtl،
   لذا text-align:left هو الذي يُحاذي النص العربي إلى اليمين فعليًا. */
p {direction:rtl; text-align:left; margin:0 0 2px 0; line-height:1.36;}
b {font-weight:700;}
.ltr {font-family:cl; direction:ltr; unicode-bidi:embed;}
.dot {font-family:cl; color:#162c4a; font-size:7pt;}
"""

CSS_NAME = "body{font-size:29pt;color:#0f2656;font-weight:700;line-height:1.15} p{margin:0}"
CSS_SUB = "body{font-size:10pt;color:#52657a} p{margin:0}"
CSS_HEAD = "body{font-size:14pt;color:#0f2656;font-weight:700} p{margin:0;line-height:1.2}"
CSS_SHEAD = "body{font-size:12.5pt;color:#162c4a;font-weight:700} p{margin:0;line-height:1.2}"
CSS_SUMMARY = "body{font-size:9.3pt;line-height:1.5;color:#24313d} p{margin:0}"
CSS_GROUP = ("body{font-size:8.7pt;color:#24313d} "
             "p{margin:0 0 2px 0;line-height:1.34} "
             ".ttl{font-size:9.6pt;font-weight:700;color:#123a5e;margin:0 0 2px 0}")
CSS_SUBHEAD = ("body{font-size:9.6pt;color:#162c4a;font-weight:700} "
               "p{margin:0 0 3px 0;line-height:1.2}")
CSS_INFO = ("body{font-size:8.7pt;color:#24313d} "
            "p{margin:0 0 3px 0;line-height:1.3} "
            ".k{color:#5c6c7c} .v{color:#162c4a;font-weight:700}")
CSS_EDU = ("body{font-size:8.9pt;color:#24313d} "
           "p{margin:0 0 3px 0;line-height:1.3} "
           ".t{font-size:9.4pt;font-weight:700;color:#123a5e;margin:0 0 1px 0} "
           ".tag{color:#162c4a;font-weight:700}")
CSS_LIST = ("body{font-size:8.7pt;color:#24313d} "
            "p{margin:0 0 3px 0;line-height:1.3}")
CSS_LANG = ("body{font-size:9pt;color:#24313d} p{margin:0;line-height:1.25}")


def ltr(s: str) -> str:
    return f'<span class="ltr">{s}</span>'


def title(t: str) -> str:
    return f'<p class="ttl">{t}</p>'


def bullet(t: str) -> str:
    return f'<p><span class="dot">•</span> {t}</p>'


def info(k: str, v: str) -> str:
    return f'<p><span class="k">{k}:</span> <span class="v">{v}</span></p>'


# ----------------------------------------------------------------------------
# المحتوى
# ----------------------------------------------------------------------------
SUMMARY_HTML = (
    "<p>خريج هندسة النفط والغاز من جامعة تونتك الماليزية " + ltr("2017/2018") + "، "
    "الأول على الدفعة بتقدير ممتاز ومعدل " + ltr("95%") + ". "
    "خبرة ميدانية في الإشراف على حفر " + ltr("12") + " بئرًا ومراقبة المكامن الإنتاجية، "
    "وتشغيل وصيانة مشاريع خدمية وإنتاجية، إلى جانب عمل إداري وتدريسي في التعليم "
    "المهني والفني والجامعي، وإجادة برامج " + ltr("Microsoft Office") + " في إعداد "
    "التقارير والجداول والمراسلات. أستكمل مرحلة تمهيدي الماجستير في إدارة الأعمال "
    "بجامعة سبأ " + ltr("2026") + "، وأسعى لتسخير هذه الخبرة في رفع كفاءة التشغيل "
    "وتطوير الأداء الفني والمؤسسي.</p>"
)

# خبرات ملف مجد (مع صياغة مهنية موسّعة كما طُلب في الملف)
MAJD_GROUPS = [
    title("مهندس حفر ومراقب جيولوجي للمكامن الإنتاجية | اليمن") +
    bullet("الإشراف الهندسي على حفر " + ltr("12") + " بئرًا ومتابعة القراءات الجيولوجية "
           "للمكامن الإنتاجية لضمان سلامة الحفر وكفاءة الإنتاج.") +
    bullet("تقييم طبقات المكامن ومتابعة مؤشرات الإنتاج بالتنسيق مع فرق الحفر والصيانة الميدانية."),

    title("مراقب تشغيل وإنتاج وصيانة | عدة مشاريع خدمية وإنتاجية") +
    bullet("مراقبة تشغيل وإنتاج وصيانة عدة مشاريع خدمية وإنتاجية، وتنظيم خطط الصيانة "
           "الدورية للحد من فترات التوقف ورفع جاهزية الأصول.") +
    bullet("متابعة مؤشرات الأداء وإعداد التقارير الفنية للإدارة لدعم قرارات التحسين."),

    title("موظف فني - الإدارة الفنية | شركة المياه والصرف الصحي") +
    bullet("تقديم الدعم الفني للإدارة الفنية في متابعة الأعمال التشغيلية وإعداد "
           "البيانات والتقارير الفنية للشركة.") +
    bullet("إعداد التقارير والجداول والمراسلات باستخدام برامج " + ltr("Microsoft Office") + "."),

    title("مدير صندوق النشء والشباب للتعليم المهني والفني | " + ltr("2020") + " - إحدى المحافظات") +
    bullet("إدارة برامج الصندوق في إحدى المحافظات ومتابعة تنفيذ مبادرات التعليم "
           "المهني والفني وتطوير آليات العمل ومتابعة فرق التنفيذ."),

    title("معيد جامعي | " + ltr("2019")) +
    bullet("الإشراف على الدروس والتمارين العملية، ودعم الطلبة أكاديميًا وبحثيًا، "
           "والمساهمة في إعداد المواد والمختبرات التعليمية."),
]

# الخبرات الموجودة أصلاً في سيرة سيف البتول (مُبقاة ومُدمجة بصيغة مختصرة)
ORIGINAL_GROUPS = [
    title("مندوب مبيعات | شركة فوج البحر - " + ltr("2025") + " حتى الآن - قطاع الجملة ومراكز التخفيضات") +
    bullet("تحقيق الهدف البيعي والتحصيلي، وإضافة عملاء جدد، ومتابعة الأهداف الفصلية والشهرية."),

    title("مندوب مبيعات | شركة ناتكو " + ltr("2023 - 2024")) +
    bullet("تحقيق الهدف البيعي والتحصيلي، والتأكد من تحقيق الانتشار وتحليل أداء العملاء."),

    title("موظف مبيعات | متجر تحف وهدايا " + ltr("2021 - 2023")) +
    bullet("استقبال العملاء وشرح المنتجات، وتحقيق أهداف البيع الشهرية وترتيب المعروضات وتحسين تجربة الشراء."),

    title("مشرف عمليات البيع وإدارة المخزون | " + ltr("2018 - 2020")) +
    bullet("متابعة عمليات البيع اليومية وتقاريرها، وتنظيم المخزون وتحديث البيانات، وتدريب الموظفين الجدد."),

    title("مسؤول التسويق | سلسلة متاجر الهدى " + ltr("2015 - 2017")) +
    bullet("إعداد الحملات التسويقية لزيادة المبيعات، ومتابعة الحسابات والمصاريف اليومية، والتعامل مع الموردين والعملاء."),

    title("مدير مشروع مياه | " + ltr("2010 - 2014")) +
    bullet("الإشراف الكامل على توزيع المياه وصيانة الشبكات، ومتابعة احتياجات المشروع ورفع التقارير، والتنسيق مع الجهات الحكومية."),
]

PERSONAL_HTML = (
    info("البريد الإلكتروني", ltr("magdalialshaheri@yahoo.com")) +
    info("رقم الجوال", ltr("0500232807")) +
    info("رقم الهاتف", ltr("00966530663905")) +
    info("الجنسية", "يمني") +
    info("تاريخ الميلاد", ltr("15/02/1994")) +
    info("الحالة الاجتماعية", "متزوج") +
    info("رخصة القيادة", "متوفرة ويجيد قيادة جميع أنواع السيارات")
)

EDU_HTML = (
    '<p class="t">بكالوريوس هندسة نفط وغاز</p>' +
    "<p>جامعة تونتك الماليزية | " + ltr("2017/2018") + "</p>" +
    '<p><span class="tag">الأول على الدفعة - بتقدير ممتاز - معدل ' + ltr("95%") + "</span></p>" +
    '<p class="t">ماجستير تمهيدي في إدارة الأعمال</p>' +
    "<p>جامعة سبأ | " + ltr("2026") + "</p>"
)

COURSES_HTML = (
    bullet("دورة اللغة الإنجليزية مستوى متقدم") +
    bullet("دورة الرخصة الدولية لقيادة الحاسب الآلي " + ltr("ICDL"))
)

SKILLS_HTML = "".join(bullet(s) for s in [
    "تنظيم وتطوير بيئة العمل",
    "حسن السيرة والسلوك",
    "تحمل ضغط العمل",
    "الاستقبال الجيد للعملاء",
    "التواصل الفعال مع العملاء",
    "الأداء الجماعي",
    "الحفاظ على أسرار العمل",
    "إجادة برامج " + ltr("Microsoft Office") + " (Word - Excel)",
])

# ----------------------------------------------------------------------------
# قياس النصوص ثم بناء التصميم
# ----------------------------------------------------------------------------
def strip_html(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", " ", fragment)
    text = re.sub(r"[ \t]+", " ", html_lib.unescape(text)).strip()
    return re.sub(r"\s+([،؛:.!?%])", r"\1", text)


def write_plain_text() -> None:
    """نسخة نصية نظيفة (Unicode) لسهولة النسخ والتعديل والبحث."""
    parts = [
        "مجد الشاهري",
        "مهندس نفط وغاز - إدارة وتشغيل المشاريع",
        "", "نبذة مختصرة", strip_html(SUMMARY_HTML), "",
        "الخبرات", "الخبرات الهندسية والإدارية",
    ]
    for index, group in enumerate(MAJD_GROUPS + ORIGINAL_GROUPS):
        if index == len(MAJD_GROUPS):
            parts.append("خبرات سابقة في المبيعات والتسويق وإدارة المشاريع")
        for line in group.split("</p>"):
            clean = strip_html(line)
            if clean:
                parts.append(clean)
        parts.append("")
    parts += ["المعلومات الشخصية"]
    for line in PERSONAL_HTML.split("</p>"):
        if strip_html(line):
            parts.append(strip_html(line))
    parts += ["", "التعليم"]
    for line in EDU_HTML.split("</p>"):
        if strip_html(line):
            parts.append(strip_html(line))
    parts += ["", "الدورات التدريبية"]
    for line in COURSES_HTML.split("</p>"):
        if strip_html(line):
            parts.append(strip_html(line))
    parts += ["", "المهارات"]
    for line in SKILLS_HTML.split("</p>"):
        if strip_html(line):
            parts.append(strip_html(line))
    parts += ["", "اللغات", "العربية: اللغة الأم", "الإنجليزية: جيد جدًا", ""]
    with open(OUT_TXT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))


def build() -> None:
    ensure_fonts()
    write_plain_text()
    arch = fitz.Archive(FONT_DIR)
    scratch = fitz.open().new_page(width=W, height=2000)

    def measure(html: str, css: str, width: float) -> float:
        spare, scale = scratch.insert_htmlbox(
            fitz.Rect(0, 0, width, 700), html, css=BASE_CSS + css,
            archive=arch, scale_low=1)
        if scale != 1 or spare < 0:
            raise RuntimeError(f"تعذّر قياس النص: spare={spare}, scale={scale}")
        return 700 - spare

    text_blocks: list[tuple[fitz.Rect, str, str]] = []
    icons: list[tuple[str, float, float]] = []   # (اسم الأيقونة، x، y بالـ pt)
    dividers: list[tuple[float, float, float, float]] = []  # (x0,y,x1,y)
    timeline_dots: list[float] = []
    bars: list[tuple[float, float, float]] = []  # (y, x0, x1) للشريط الداكن

    def add(rect, html, css):
        text_blocks.append((fitz.Rect(*rect), html, BASE_CSS + css))

    # ---- رأس الصفحة ----
    add((25, 45, 360, 88), "<p>مجد الشاهري</p>", CSS_NAME)
    add((25, 90, 360, 107), "<p>مهندس نفط وغاز - إدارة وتشغيل المشاريع</p>", CSS_SUB)

    # ---- نبذة مختصرة ----
    add((25, 130, 318, 157), "<p>نبذة مختصرة</p>", CSS_HEAD)
    icons.append(("about", 334, 144))
    sy = 161
    sh = measure(SUMMARY_HTML, CSS_SUMMARY, 328)
    add((25, sy, 353, sy + sh + 2), SUMMARY_HTML, CSS_SUMMARY)
    y = sy + sh + 8
    dividers.append((25, y, 360, y))

    # ---- الخبرات ----
    y += 9
    add((25, y, 318, y + 25), "<p>الخبرات</p>", CSS_HEAD)
    icons.append(("experience", 334, y + 12))
    y += 29

    sub1 = "<p>الخبرات الهندسية والإدارية</p>"
    h = measure(sub1, CSS_SUBHEAD, 323)
    add((25, y, 348, y + h + 2), sub1, CSS_SUBHEAD)
    y += h + 5
    timeline_start = y
    for html in MAJD_GROUPS:
        h = measure(html, CSS_GROUP, 323)
        add((25, y, 348, y + h + 2), html, CSS_GROUP)
        timeline_dots.append(y + 5)
        y += h + 4

    sub2 = "<p>خبرات سابقة في المبيعات والتسويق وإدارة المشاريع</p>"
    h = measure(sub2, CSS_SUBHEAD, 323)
    add((25, y, 348, y + h + 2), sub2, CSS_SUBHEAD)
    y += h + 5
    for html in ORIGINAL_GROUPS:
        h = measure(html, CSS_GROUP, 323)
        add((25, y, 348, y + h + 2), html, CSS_GROUP)
        timeline_dots.append(y + 5)
        y += h + 4
    timeline_end = y - 2

    # ---- العمود الأيمن ----
    X0, X1, HEAD1 = 385, 585, 548

    def right_section(icon: str, heading: str, html: str, css: str,
                      width: float, gap_after: float = 9):
        nonlocal ry
        add((X0, ry, HEAD1, ry + 24), f"<p>{heading}</p>", CSS_SHEAD)
        icons.append((icon, 566, ry + 12))
        dividers.append((395, ry + 26, 548, ry + 26))
        ry += 31
        h = measure(html, css, width)
        add((X0, ry, X1, ry + h + 2), html, css)
        ry += h + gap_after
        return ry

    ry = 255.0
    right_section("personal", "المعلومات الشخصية", PERSONAL_HTML, CSS_INFO, X1 - X0)
    dividers.append((RIGHT_X, ry, W, ry)); ry += 9
    right_section("education", "التعليم", EDU_HTML, CSS_EDU, X1 - X0)
    dividers.append((RIGHT_X, ry, W, ry)); ry += 9
    right_section("courses", "الدورات التدريبية", COURSES_HTML, CSS_LIST, X1 - X0)
    dividers.append((RIGHT_X, ry, W, ry)); ry += 9
    right_section("skills", "المهارات", SKILLS_HTML, CSS_LIST, X1 - X0)
    dividers.append((RIGHT_X, ry, W, ry)); ry += 9

    add((X0, ry, HEAD1, ry + 24), "<p>اللغات</p>", CSS_SHEAD)
    icons.append(("languages", 566, ry + 12))
    ry += 27
    add((X0, ry, X1, ry + 15), "<p>العربية: اللغة الأم</p>", CSS_LANG)
    bars.append((ry + 17, X0, 545))           # العربية: الشريط ممتلئ
    add((X0, ry + 30, X1, ry + 45), "<p>الإنجليزية: جيد جدًا</p>", CSS_LANG)
    bars.append((ry + 47, X0, 510))           # الإنجليزية: ~80%
    ry += 56

    if y > H - 12 or ry > H - 12:
        print(f"تحذير: ارتفاع المحتوى الأيسر={y:.1f}، الأيمن={ry:.1f}، ارتفاع الصفحة={H}")

    # ------------------------------------------------------------------------
    # الخلفية (ألوان، إطار الصورة، الأيقونات، الخطوط الفاصلة)
    # ------------------------------------------------------------------------
    bg = Image.new("RGB", (round(W * S), round(H * S)), "white")
    d = ImageDraw.Draw(bg)

    # الشريط الكحلي العلوي مع القصّة المائلة البيضاء
    d.rectangle([RIGHT_X * S, 0, W * S, 247 * S], fill=NAVY)
    wedge = [(RIGHT_X * S, 0)]
    for i in range(31):
        t = i / 30
        x = 401 - 26 * t
        yy = 47 * (t ** 1.7)
        wedge.append((round(x * S), round(yy * S)))
    wedge.append((RIGHT_X * S, 47 * S))
    d.polygon(wedge, fill="white")

    # العمود الأيمن الرمادي
    d.rounded_rectangle([RIGHT_X * S, 247 * S, (W + 20) * S, H * S],
                        radius=16 * S, fill=SIDEBAR)

    # إطار الصورة + الصورة المرفقة
    d.rounded_rectangle([401 * S, 6 * S, 573 * S, 235 * S], radius=18 * S,
                        fill="white", outline=NAVY, width=round(2 * S))
    photo = Image.open(SRC_PHOTO).convert("RGB")
    pw, ph = round(162 * S), round(219 * S)
    photo = ImageOps.fit(photo, (pw, ph), method=Image.LANCZOS, centering=(0.5, 0.32))
    mask = Image.new("L", (pw, ph), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, pw - 1, ph - 1],
                                          radius=14 * S, fill=255)
    bg.paste(photo, (round(406 * S), round(11 * S)), mask)

    # خط تحت الاسم
    d.line([25 * S, 112 * S, 252 * S, 112 * S], fill=TITLE, width=max(1, round(1 * S)))
    d.ellipse([249 * S, 109 * S, 255 * S, 115 * S], fill=TITLE)

    # خطوط فاصلة
    for x0, yy, x1, _ in dividers:
        d.line([x0 * S, yy * S, x1 * S, yy * S], fill=GRAY, width=max(1, round(0.8 * S)))

    # أشرطة مستوى اللغات
    for yy, x0, x1 in bars:
        d.rounded_rectangle([x0 * S, yy * S, 545 * S, (yy + 5) * S],
                            radius=2.5 * S, fill=(228, 232, 238))
        d.rounded_rectangle([x0 * S, yy * S, x1 * S, (yy + 5) * S],
                            radius=2.5 * S, fill=NAVY)

    # الخط الزمني للخبرات ونقاطه
    d.line([355 * S, timeline_start * S, 355 * S, timeline_end * S],
           fill=NAVY, width=max(1, round(0.7 * S)))
    for yy in timeline_dots:
        d.ellipse([352.6 * S, (yy - 2.6) * S, 357.4 * S, (yy + 2.6) * S], fill=NAVY)

    # الأيقونات الدائرية مأخوذة من تصميم السيرة الأصلية
    src = fitz.open(SRC_CV)
    xref = src[0].get_images(full=True)[0][0]
    src_img = Image.open(io.BytesIO(src.extract_image(xref)["image"])).convert("RGBA")
    src.close()
    icon_centers = {
        "about": (595, 272), "personal": (970, 465), "experience": (590, 545),
        "education": (970, 858), "courses": (970, 987),
        "skills": (970, 1122), "languages": (970, 1392),
    }
    size = round(26 * S)
    for name, cx, cy in icons:
        sx, sy = icon_centers[name]
        crop = src_img.crop((sx - 27, sy - 27, sx + 27, sy + 27)).resize(
            (size, size), Image.LANCZOS)
        alpha = Image.new("L", (size, size), 0)
        ImageDraw.Draw(alpha).ellipse([1, 1, size - 2, size - 2], fill=255)
        crop.putalpha(alpha)
        bg.paste(crop, (round(cx * S - size / 2), round(cy * S - size / 2)), crop)

    buf = io.BytesIO()
    bg.save(buf, format="PNG", optimize=True)
    bg_bytes = buf.getvalue()

    # ------------------------------------------------------------------------
    # كتابة ملف PDF
    # ------------------------------------------------------------------------
    doc = fitz.open()
    page = doc.new_page(width=W, height=H)
    page.insert_image(fitz.Rect(0, 0, W, H), stream=bg_bytes)
    for rect, html, css in text_blocks:
        spare, scale = page.insert_htmlbox(rect, html, css=css,
                                           archive=arch, scale_low=1)
        if scale != 1 or spare < -1:
            print(f"تحذير: نص ضيق في {rect}: spare={spare:.1f}, scale={scale}")
    doc.set_metadata({
        "title": "مجد الشاهري - السيرة الذاتية",
        "author": "مجد الشاهري",
        "subject": "سيرة ذاتية محدّثة بدمج معلومات ملف مجد والصورة الشخصية",
        "creator": "Arena Agent Mode",
    })
    doc.save(OUT_PDF, garbage=4, deflate=True)
    doc[0].get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False).save(OUT_PNG)
    doc.close()
    print("تم إنشاء:", OUT_PDF)
    print("المعاينة:", OUT_PNG)
    print("النسخة النصية:", OUT_TXT)
    print(f"كتل النص={len(text_blocks)}، نهاية العمود الأيسر={y:.1f}pt، "
          f"نهاية العمود الأيمن={ry:.1f}pt من أصل {H:.1f}pt")


if __name__ == "__main__":
    build()
