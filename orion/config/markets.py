"""Market registry. Markets and options are config; the graph never hardcodes them.

Add a new market by defining a Market and registering it in MARKETS. Every question has English and Arabic
wording; answers are stored with the English choice values whatever language the customer uses.
"""

from typing import Optional

from pydantic import BaseModel

from orion.config.size_charts import SIZE_CHARTS
from orion.config.garment_zones import zones_for
from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, Question, Section

CUSTOM_OPTION = "custom"


class Option(BaseModel):
    id: str
    name: str
    name_ar: str
    questions: list[Question] = []
    first_questions: list[Question] = []   # asked before the market's common questions
    uses_common_questions: bool = True
    mockup: Optional[str] = None     # garment drawing for placement questions (web/lib/mockups.ts)


class Market(BaseModel):
    id: str
    name: str
    name_ar: str
    common_questions: list[Question]
    options: dict[str, Option]
    # Saudi import rules are UNVERIFIED; anything here is flagged to the team, never quoted blindly.
    compliance_notes: list[str] = []


def choice(
    id: str, prompt: str, prompt_ar: str, options: list[tuple], *,
    section: Section = "design", multiple: bool = False, allow_other: bool = True, required: bool = True,
    hint: Optional[str] = None, hint_ar: Optional[str] = None, brand: Optional[str] = None,
) -> Question:
    """A multiple-choice question. `options` are (English value, Arabic label) or
    (English value, Arabic label, cost tier 1-3) for a relative $ / $$ / $$$ hint."""
    tiers = [o[2] if len(o) > 2 else 0 for o in options]
    return Question(
        id=id, prompt=prompt, prompt_ar=prompt_ar, type="choice", section=section,
        choices=[o[0] for o in options], choices_ar=[o[1] for o in options],
        cost_tiers=tiers if any(tiers) else [],
        multiple=multiple, allow_other=allow_other, required=required, hint=hint, hint_ar=hint_ar, brand=brand,
    )


# Relative cost tiers below are general guidance for China production.
# TODO(decide): the team confirms or adjusts them per market.


# --- Fashion, apparel & uniforms -------------------------------------------------
# Everything a garment factory always needs is asked here; the AI only asks what is specific to an order.

def _size_table(prompt="How many pieces per size?", prompt_ar="كم قطعة لكل مقاس؟", example="S:20, M:50, L:50, XL:30"):
    return Question(
        id=SIZE_TABLE_ID, prompt=prompt, prompt_ar=prompt_ar, type="size_table", section="quantity",
        hint=f"e.g. {example}", hint_ar=f"مثال: {example}",
    )


_SIZE_STANDARD = choice(
    "size_standard", "Which size standard?", "ما معيار المقاسات؟",
    [("US/EU sizing", "مقاسات أمريكية/أوروبية"), ("Asian sizing", "مقاسات آسيوية"),
     ("factory standard", "معيار المصنع")],
    section="quantity",
    hint="Chinese factories use Asian sizing unless told otherwise; it runs about one size smaller. "
         "Under Other you can give your own measurements.",
    hint_ar="المصانع الصينية تستخدم المقاسات الآسيوية ما لم يُطلب غير ذلك، وهي أصغر بمقاس تقريبًا. "
            "في «أخرى» يمكنك كتابة مقاساتك الخاصة.",
)
_LABELS = choice(
    "labels", "Which labels do you need?", "ما الملصقات التي تحتاجها؟",
    [("woven neck label with logo", "ملصق رقبة منسوج بالشعار", 2), ("printed neck label", "ملصق رقبة مطبوع", 1),
     ("size label", "ملصق المقاس", 1), ("care label", "ملصق العناية", 1), ("hang tag", "بطاقة معلّقة", 2),
     ("no labels", "بدون ملصقات")],
    section="quality", multiple=True,
)
_FABRIC_GSM = Question(
    id="fabric_gsm", prompt="Fabric weight in GSM (grams per square metre)?",
    prompt_ar="وزن القماش بالغرام لكل متر مربع (GSM)؟", type="number", section="quality",
    hint="T-shirts are usually 160-240, hoodies 280-400. Ask Orion if you are unsure.",
    hint_ar="التيشيرتات عادةً 160-240، والهوديز 280-400. اسأل أوريون إن لم تكن متأكدًا.",
)


_NEEDED_BY = choice(
    "needed_by", "When do you need the order?", "متى تحتاج الطلب؟",
    [("within 1 month", "خلال شهر"), ("in 1-2 months", "خلال شهر إلى شهرين"),
     ("in 2-3 months", "خلال شهرين إلى ثلاثة"), ("flexible", "مرن")],
    section="quantity",
    hint="Production and shipping from China usually take 4-8 weeks in total. Under Other you can give a date.",
    hint_ar="الإنتاج والشحن من الصين يستغرقان عادةً من 4 إلى 8 أسابيع. في «أخرى» يمكنك كتابة تاريخ.",
)


_GENDER = choice("gender", "Gender?", "الفئة؟",
                 [("unisex", "للجنسين"), ("men", "رجالي"), ("women", "نسائي"), ("kids", "أطفال")])
_SEASON = choice("season", "Season?", "الموسم؟",
                 [("winter", "الشتاء"), ("autumn", "الخريف"), ("spring", "الربيع"), ("summer", "الصيف"),
                  ("all seasons", "كل المواسم")], multiple=True, required=False)
_SUPPLY = choice(
    "supply_type", "Supply type?", "نوع التوريد؟",
    [("OEM service", "تصنيع بتصميمك وشعارك (OEM)"), ("ODM service", "تصميم المصنع مع شعارك (ODM)"),
     ("ready stock with your logo", "منتج جاهز مع شعارك")],
    hint="OEM: the factory makes your own design. ODM: you pick one of the factory's designs and add your brand.",
    hint_ar="OEM: يصنع المصنع تصميمك أنت. ODM: تختار من تصاميم المصنع وتضيف علامتك.",
)


# Each product's own attributes, asked before everything else: the full checklist a factory needs for it,
# so the AI only has to ask what is specific to one order.
_HOODIE_FIRST = [
    choice("hoodie_style", "Type?", "النوع؟",
           [("pullover", "بدون سحّاب (Pullover)", 1), ("zip-up", "بسحّاب كامل", 2), ("half-zip", "بنصف سحّاب", 2)],
           allow_other=False),
    choice("collar", "Collar?", "الياقة؟",
           [("hooded", "بقلنسوة"), ("double-layer hood", "قلنسوة بطبقتين"), ("crew neck", "ياقة دائرية بدون قلنسوة"),
            ("mock neck", "ياقة مرتفعة"), ("funnel neck", "ياقة عالية واسعة")]),
    choice("fabric", "Fabric type?", "نوع النسيج؟",
           [("knitted fleece (brushed inside)", "صوف محبوك (فليس من الداخل)"), ("french terry", "فرنش تيري"),
            ("jersey knit", "جيرسي محبوك"), ("waffle knit", "وافل محبوك"), ("woven", "منسوج")]),
    choice("material", "Material?", "الخامة؟",
           [("100% cotton", "قطن 100%", 2), ("cotton-polyester 80/20", "قطن وبوليستر 80/20", 1),
            ("cotton-polyester 60/40", "قطن وبوليستر 60/40", 1), ("100% polyester", "بوليستر 100%", 1),
            ("organic cotton", "قطن عضوي", 3), ("recycled polyester", "بوليستر معاد تدويره", 2),
            ("cotton-spandex", "قطن وسباندكس", 2)]),
    choice("fit_type", "Fit type?", "نوع القصّة؟",
           [("regular", "عادية"), ("loose", "واسعة"), ("oversized", "أوفر سايز"), ("boxy", "مربعة (Boxy)"),
            ("slim", "ضيقة")]),
    choice("design", "Design details?", "تفاصيل التصميم؟",
           [("plain", "سادة"), ("cut out", "بفتحات (Cut out)"), ("distressed", "ممزق (Distressed)"),
            ("colour block", "ألوان متداخلة (Colour block)"), ("patchwork", "رقع (Patchwork)"),
            ("raw hem", "حافة غير مخيطة"), ("side slits", "فتحات جانبية")], multiple=True, required=False),
    choice("length", "Length?", "الطول؟", [("regular", "عادي"), ("crop", "قصير (Crop)"), ("longline", "طويل")]),
    choice("sleeve_style", "Sleeve style?", "نوع الأكمام؟",
           [("regular", "عادية"), ("drop shoulder", "كتف ساقط"), ("raglan", "راجلان"), ("batwing", "خفاشية")]),
    choice("pattern_type", "Pattern type?", "النقشة؟",
           [("solid", "سادة"), ("colour block", "ألوان متداخلة"), ("all-over print", "طباعة كاملة"),
            ("tie-dye", "تاي داي"), ("camouflage", "مموّه"), ("striped", "مخطط"), ("graphic or letters", "رسومات أو حروف")]),
    choice("style", "Style?", "الطابع؟",
           [("oversized", "أوفر سايز"), ("boxy", "مربع"), ("fashion", "عصري"), ("unisex", "للجنسين"),
            ("pullover", "بدون سحّاب"), ("sweatshirt", "سويت شيرت"), ("streetwear", "ستريت وير"), ("casual", "كاجوال"),
            ("sporty", "رياضي"), ("minimalist", "بسيط")], multiple=True, required=False),
    choice("features", "Features?", "المزايا؟",
           [("breathable", "يسمح بالتهوية"), ("warm", "دافئ"), ("anti-pilling", "مقاوم للوبر"),
            ("anti-shrink", "مقاوم للانكماش"), ("quick-dry", "سريع الجفاف"), ("water-resistant", "مقاوم للماء"),
            ("eco-friendly", "صديق للبيئة")], multiple=True, required=False),
    _GENDER,
    _SEASON,
    _SUPPLY,
]

_TEE_FIRST = [
    choice("neckline", "Neckline?", "شكل الياقة؟",
           [("crew neck", "ياقة دائرية"), ("mock neck", "ياقة مرتفعة"), ("v-neck", "ياقة V"),
            ("henley", "ياقة بأزرار (Henley)", 2), ("wide neck", "ياقة واسعة")]),
    choice("fabric", "Fabric type?", "نوع النسيج؟",
           [("jersey knit", "جيرسي محبوك"), ("french terry", "فرنش تيري", 2), ("pique", "بيكيه"),
            ("waffle knit", "وافل محبوك", 2), ("slub", "سلب (نسيج غير منتظم)", 2)]),
    choice("material", "Material?", "الخامة؟",
           [("100% cotton", "قطن 100%", 2), ("combed cotton", "قطن ممشط", 2), ("heavyweight cotton", "قطن ثقيل", 3),
            ("cotton-polyester 60/40", "قطن وبوليستر 60/40", 1), ("100% polyester", "بوليستر 100%", 1),
            ("organic cotton", "قطن عضوي", 3), ("cotton-spandex", "قطن وسباندكس", 2)]),
    choice("fit_type", "Fit type?", "نوع القصّة؟",
           [("oversized", "أوفر سايز"), ("boxy", "مربعة (Boxy)"), ("relaxed", "مريحة"), ("regular", "عادية")]),
    choice("length", "Length?", "الطول؟", [("regular", "عادي"), ("crop", "قصير (Crop)"), ("longline", "طويل")]),
    choice("sleeve_style", "Sleeves?", "الأكمام؟",
           [("short, drop shoulder", "قصيرة بكتف ساقط"), ("short, regular", "قصيرة عادية"),
            ("half sleeve", "نصف كم"), ("long sleeve", "طويلة")]),
    choice("design", "Design details?", "تفاصيل التصميم؟",
           [("plain", "سادة"), ("chest pocket", "جيب صدر"), ("raw hem", "حافة غير مخيطة"), ("side slits", "فتحات جانبية"),
            ("distressed", "ممزق (Distressed)"), ("colour block", "ألوان متداخلة")], multiple=True, required=False),
    choice("pattern_type", "Pattern type?", "النقشة؟",
           [("solid", "سادة"), ("all-over print", "طباعة كاملة", 2), ("tie-dye", "تاي داي", 2), ("striped", "مخطط"),
            ("graphic or letters", "رسومات أو حروف")]),
    choice("wash", "Fabric finish?", "معالجة القماش؟",
           [("no wash", "بدون معالجة", 1), ("garment dyed", "مصبوغ بعد الخياطة", 2), ("acid wash", "غسيل أسيد", 2),
            ("enzyme washed (soft)", "غسيل إنزيمي (ناعم)", 2), ("pre-shrunk", "معالج ضد الانكماش", 1)],
           required=False),
    choice("style", "Style?", "الطابع؟",
           [("streetwear", "ستريت وير"), ("casual", "كاجوال"), ("sporty", "رياضي"), ("minimalist", "بسيط"),
            ("unisex", "للجنسين")], multiple=True, required=False),
    choice("features", "Features?", "المزايا؟",
           [("breathable", "يسمح بالتهوية"), ("anti-pilling", "مقاوم للوبر"), ("anti-shrink", "مقاوم للانكماش"),
            ("quick-dry", "سريع الجفاف"), ("eco-friendly", "صديق للبيئة")], multiple=True, required=False),
    _GENDER,
    _SEASON,
    _SUPPLY,
]

_ABAYA_FIRST = [
    choice("abaya_style", "Abaya cut?", "قصّة العباية؟",
           [("open front (bisht cut)", "مفتوحة من الأمام (قصة بشت)"), ("closed", "مغلقة"), ("kimono", "كيمونو"),
            ("butterfly (farasha)", "فراشة"), ("wrap", "ملفوفة")]),
    choice("fabric", "Fabric?", "القماش؟",
           [("crepe", "كريب", 2), ("nida", "ندى", 3), ("linen", "كتان", 2), ("chiffon", "شيفون", 2),
            ("satin", "ساتان", 2), ("jersey", "جيرسي", 1)]),
    choice("material", "Material?", "الخامة؟",
           [("polyester", "بوليستر", 1), ("viscose", "فسكوز", 2), ("silk blend", "مزيج حرير", 3),
            ("linen blend", "مزيج كتان", 2), ("cotton", "قطن", 2)], required=False,
           hint="Not sure? The fabric choice is enough; the factory will suggest the usual material.",
           hint_ar="غير متأكد؟ يكفي اختيار القماش، وسيقترح المصنع الخامة المعتادة."),
    choice("sleeve_style", "Sleeve style?", "شكل الأكمام؟",
           [("straight", "مستقيمة"), ("wide/bisht", "واسعة (بشت)"), ("cuffed", "بأساور"), ("bell", "جرسية"),
            ("batwing", "خفاشية")]),
    choice("neckline", "Neckline?", "فتحة الرقبة؟",
           [("round", "دائرية"), ("v-neck", "على شكل V"), ("collar", "بياقة"), ("hooded", "بقلنسوة")]),
    choice("closure", "Closure?", "طريقة الإغلاق؟",
           [("no closure (open)", "بدون إغلاق (مفتوحة)"), ("snap buttons", "كبسات"), ("hidden buttons", "أزرار مخفية"),
            ("zip", "سحّاب"), ("belt or tie", "حزام أو ربطة")]),
    choice("lining", "Lining?", "البطانة؟",
           [("no lining", "بدون بطانة", 1), ("half lining", "بطانة جزئية", 2), ("full lining", "بطانة كاملة", 3)]),
    choice("shayla", "Matching shayla (scarf)?", "شيلة مطابقة؟",
           [("yes", "نعم", 2), ("no", "لا")], allow_other=False),
    choice("embellishment", "Any embellishment?", "هل تريد زخرفة؟",
           [("none", "بدون"), ("embroidery", "تطريز", 2), ("beading", "خرز", 3), ("lace", "دانتيل", 2),
            ("trims", "شرائط وزينة", 1), ("contrast piping", "حواف بلون مختلف", 1)], multiple=True),
    choice("pattern_type", "Pattern?", "النقشة؟",
           [("solid", "سادة"), ("two-tone", "لونان"), ("printed", "مطبوعة", 2), ("embroidered panels", "أجزاء مطرزة", 3)]),
    choice("style", "Occasion?", "المناسبة؟",
           [("daily", "يومية"), ("work", "للعمل"), ("formal occasion", "مناسبات رسمية"), ("travel", "للسفر")],
           multiple=True, required=False),
    _SEASON,
    _SUPPLY,
]

_TOTE_FIRST = [
    choice("bag_style", "Bag style?", "نوع الحقيبة؟",
           [("open top tote", "مفتوحة من الأعلى"), ("zipper tote", "بسحّاب", 2), ("tote with gusset (box base)", "بقاعدة عريضة", 2),
            ("drawstring bag", "بحبل سحب", 1), ("foldable tote", "قابلة للطي", 2)]),
    choice("fabric", "Fabric?", "القماش؟",
           [("cotton canvas", "كانفاس قطني", 2), ("cotton", "قطن", 1), ("non-woven", "قماش غير منسوج", 1),
            ("jute", "جوت", 2), ("recycled PET", "بوليستر معاد تدويره", 2), ("polyester", "بوليستر", 1)]),
    choice("fabric_weight", "Fabric weight?", "سماكة القماش؟",
           [("light (140-200 gsm)", "خفيف (140-200 غرام)", 1), ("medium (220-280 gsm)", "متوسط (220-280 غرام)", 2),
            ("heavy (300-400 gsm)", "ثقيل (300-400 غرام)", 3)]),
    choice("dimensions", "Bag size?", "مقاس الحقيبة؟",
           [("small 30x35cm", "صغيرة 30×35 سم"), ("standard 38x42cm", "عادية 38×42 سم"),
            ("large 40x45x10cm", "كبيرة 40×45×10 سم")],
           hint="Under Other: width x height x gusset in cm.",
           hint_ar="في «أخرى»: العرض × الارتفاع × العمق بالسنتيمتر."),
    choice("handle_type", "Handles?", "المقابض؟",
           [("same fabric straps", "من نفس القماش", 1), ("cotton webbing", "شريط قطني", 1), ("rope", "حبل", 2),
            ("leather", "جلد", 3)]),
    Question(id="handle_length", prompt="Handle length (cm)?", prompt_ar="طول المقبض (سم)؟", type="number",
             hint="Shoulder bags usually 60-70 cm, hand-carry 30-40 cm.",
             hint_ar="حقائب الكتف عادةً 60-70 سم، وحمل اليد 30-40 سم."),
    choice("closure", "Closure?", "الإغلاق؟",
           [("none", "بدون"), ("zipper", "سحّاب", 2), ("snap button", "كبسة", 1), ("magnetic button", "زر مغناطيسي", 1)]),
    choice("pockets", "Pockets?", "الجيوب؟",
           [("none", "بدون"), ("inside pocket", "جيب داخلي", 1), ("outside pocket", "جيب خارجي", 1)], multiple=True),
    choice("lining", "Lining?", "البطانة؟", [("no lining", "بدون بطانة", 1), ("lined", "مبطنة", 2)]),
    choice("features", "Features?", "المزايا؟",
           [("eco-friendly", "صديقة للبيئة"), ("water-resistant coating", "طبقة مقاومة للماء"),
            ("reinforced stitching", "خياطة مقواة"), ("foldable", "قابلة للطي")], multiple=True, required=False),
    _SUPPLY,
]

_UNIFORM_FIRST = [
    choice("garment_type", "Which garments?", "ما القطع المطلوبة؟",
           [("polo shirt", "قميص بولو"), ("dress shirt", "قميص رسمي"), ("t-shirt", "تيشيرت"),
            ("trousers", "بنطال"), ("jacket", "جاكيت"), ("apron", "مريلة"), ("cap", "قبعة")], multiple=True),
    choice("use", "Where will it be worn?", "أين سيُلبس؟",
           [("office", "مكتب"), ("cafe or restaurant front", "مقهى أو صالة مطعم"), ("kitchen", "مطبخ"),
            ("retail store", "متجر"), ("field or warehouse", "ميدان أو مستودع"), ("medical", "طبي")]),
    choice("fabric", "Fabric?", "القماش؟",
           [("cotton", "قطن", 2), ("poly-cotton", "بولي قطن", 1), ("polyester", "بوليستر", 1),
            ("pique (for polos)", "بيكيه (للبولو)", 1), ("gabardine", "جبردين", 3), ("twill", "تويل", 2)]),
    choice("fit_type", "Fit?", "القصّة؟", [("regular", "عادية"), ("slim", "ضيقة"), ("relaxed", "مريحة")]),
    choice("sleeve_style", "Sleeves?", "الأكمام؟",
           [("short", "قصيرة"), ("long", "طويلة"), ("both (separate sets)", "الاثنان (أطقم منفصلة)")]),
    choice("collar", "Collar (for shirts)?", "الياقة (للقمصان)؟",
           [("polo collar", "ياقة بولو"), ("classic collar", "ياقة كلاسيكية"), ("mandarin collar", "ياقة ماندرين"),
            ("crew neck", "ياقة دائرية")], required=False),
    choice("pockets", "Pockets?", "الجيوب؟",
           [("chest pocket", "جيب صدر"), ("pen pocket", "جيب قلم"), ("no pocket", "بدون جيب")], multiple=True,
           required=False),
    choice("features", "Features?", "المزايا؟",
           [("stain-resistant", "مقاوم للبقع", 2), ("wrinkle-free", "لا يتجعد", 2), ("breathable", "يسمح بالتهوية"),
            ("stretch", "مرن"), ("moisture-wicking", "يطرد الرطوبة", 2)], multiple=True, required=False),
    choice("gender", "Gender?", "الفئة؟",
           [("unisex", "للجنسين"), ("men", "رجالي"), ("women", "نسائي"), ("men and women (separate cuts)", "رجالي ونسائي (قصّات منفصلة)")]),
    _SUPPLY,
]


APPAREL = Market(
    id="apparel",
    name="Fashion, apparel & uniforms",
    name_ar="الأزياء والملابس والزي الموحد",
    common_questions=[
        choice(
            "colors", "Garment colors?", "ما ألوان القطعة؟",
            [("black", "أسود"), ("white", "أبيض"), ("navy", "كحلي"), ("grey", "رمادي"), ("beige", "بيج"),
             ("olive", "زيتي")],
            multiple=True, brand="colors",
            hint="Under Other you can add a Pantone or HEX code.",
            hint_ar="في «أخرى» يمكنك إضافة رمز اللون (Pantone أو HEX).",
        ),
        Question(
            id="color_zones", prompt="Colour each part (optional)", prompt_ar="لوّن كل جزء (اختياري)",
            type="color_zones", required=False,
            hint="Tap a part of the garment and pick its colour, or use the palette above for one colour overall.",
            hint_ar="اضغط على جزء من القطعة واختر لونه، أو استخدم الألوان أعلاه للون واحد.",
        ),
        choice(
            "decoration_method", "How should the logo/design be applied?", "كيف يُطبَّق الشعار أو التصميم؟",
            [("screen print", "طباعة شاشة (سلك سكرين)", 1), ("DTG print", "طباعة رقمية مباشرة (DTG)", 2),
             ("embroidery", "تطريز", 3), ("heat transfer", "طباعة حرارية", 1), ("no logo", "بدون شعار")],
        ),
        Question(
            id="artwork", prompt="Upload your logo or artwork.", prompt_ar="ارفع شعارك أو التصميم.",
            type="file", required=False, brand="logo",
            hint="PNG, JPG, SVG, PDF, AI or EPS, up to 10 MB. Vector files (SVG, AI, EPS, PDF) print and embroider best.",
            hint_ar="PNG أو JPG أو SVG أو PDF أو AI أو EPS، حتى 10 ميغابايت. الملفات المتجهة (SVG وAI وEPS وPDF) أفضل للطباعة والتطريز.",
        ),
        Question(
            id="decoration_placement", prompt="Where do the logo and labels go, and how big?",
            prompt_ar="أين يوضع الشعار والملصقات، وما حجمها؟", type="placement", required=False,
            hint="Add a picture of each logo or label, then drag it into place and drag the corner to resize.",
            hint_ar="أضف صورة كل شعار أو ملصق، ثم اسحبها إلى مكانها واسحب الزاوية لتغيير الحجم.",
        ),
        _NEEDED_BY,
        choice(
            "packaging", "How should each piece be packed?", "كيف تُغلَّف كل قطعة؟",
            [("individual polybag", "كيس بلاستيكي لكل قطعة", 1), ("polybag with size sticker", "كيس مع ملصق المقاس", 1),
             ("folded with tissue paper", "مطوية بورق مناديل", 2), ("on a hanger", "على علّاقة", 2),
             ("branded box", "علبة تحمل شعارك", 3), ("bulk, no individual packing", "بالجملة دون تغليف فردي", 1)],
            section="quality", multiple=True,
        ),
        choice(
            "sample", "Do you want a sample before full production?", "هل تريد عينة قبل الإنتاج الكامل؟",
            [("yes, sample first", "نعم، عينة أولًا"), ("no, go straight to production", "لا، مباشرة للإنتاج"),
             ("not sure", "غير متأكد")],
            section="quality", allow_other=False,
            hint="A sample takes about 1-2 weeks and lets you check the product before the full order.",
            hint_ar="العينة تستغرق أسبوعًا إلى أسبوعين تقريبًا، وتتيح لك فحص المنتج قبل الطلب الكامل.",
        ),
    ],
    options={
        "hoodie": Option(
            id="hoodie", name="Hoodie", name_ar="هودي", mockup="hoodie",
            first_questions=_HOODIE_FIRST,
            questions=[
                _FABRIC_GSM,
                choice("drawstrings", "Hood drawstrings?", "حبال القلنسوة؟",
                       [("flat cotton", "حبال قطنية مسطحة"), ("round cord", "حبل دائري"),
                        ("no drawstrings", "بدون حبال")]),
                choice("pocket", "Pocket?", "الجيب؟",
                       [("kangaroo pocket", "جيب كنغر"), ("side pockets", "جيوب جانبية"), ("no pocket", "بدون جيب")]),
                _size_table(),
                _SIZE_STANDARD,
                _LABELS,
            ],
        ),
        "oversized_tee": Option(
            id="oversized_tee", name="Oversized T-shirt", name_ar="تيشيرت واسع", mockup="tee",
            first_questions=_TEE_FIRST,
            questions=[_FABRIC_GSM, _size_table(), _SIZE_STANDARD, _LABELS],
        ),
        "abaya": Option(
            id="abaya", name="Abaya", name_ar="عباية", mockup="abaya",
            first_questions=_ABAYA_FIRST,
            questions=[
                Question(
                    id="abaya_length", prompt="Abaya length per size (cm)?", prompt_ar="طول العباية لكل مقاس (سم)؟",
                    type="text", section="quantity",
                    hint="e.g. 52: 132cm, 54: 137cm, 56: 142cm", hint_ar="مثال: 52: 132 سم، 54: 137 سم، 56: 142 سم",
                ),
                _size_table("How many pieces per size?", "كم قطعة لكل مقاس؟", "52:10, 54:20, 56:20, 58:10"),
                _LABELS,
            ],
        ),
        "tote_bag": Option(
            id="tote_bag", name="Tote bag", name_ar="حقيبة قماشية", mockup="tote",
            first_questions=_TOTE_FIRST,
            questions=[
                Question(id=QUANTITY_ID, prompt="How many bags?", prompt_ar="كم حقيبة؟", type="number",
                         section="quantity"),
            ],
        ),
        "corporate_uniform": Option(
            id="corporate_uniform", name="Corporate uniform", name_ar="زي موحد للشركات", mockup="polo",
            first_questions=_UNIFORM_FIRST,
            questions=[
                _FABRIC_GSM.model_copy(update={"required": False}),
                _size_table("Staff count per size?", "عدد الموظفين لكل مقاس؟", "S:5, M:12, L:10, XL:4"),
                _SIZE_STANDARD,
                _LABELS,
            ],
        ),
        CUSTOM_OPTION: Option(
            id=CUSTOM_OPTION, name="Something else (custom)", name_ar="شيء آخر (مخصص)", uses_common_questions=False,
            # The customer describes it in their own words (and pictures); the AI then asks everything else
            questions=[
                Question(
                    id="description", prompt="Describe what you want to make", prompt_ar="صف ما تريد صنعه",
                    type="text", multiline=True,
                    hint="What is it, who is it for, materials, colours, size, logo... write as much as you know.",
                    hint_ar="ما هو، ولمن، والخامات، والألوان، والمقاس، والشعار... اكتب كل ما تعرفه.",
                ),
                Question(
                    id="reference_images", prompt="Add pictures or sketches", prompt_ar="أضف صورًا أو رسومات",
                    type="file", required=False,
                    hint="A photo of a similar product or your own sketch helps a lot.",
                    hint_ar="صورة لمنتج مشابه أو رسمة منك تساعد كثيرًا.",
                ),
                Question(id=QUANTITY_ID, prompt="How many pieces?", prompt_ar="كم قطعة؟", type="number",
                         section="quantity"),
                _NEEDED_BY,
            ],
        ),
    },
    compliance_notes=[
        "Textile labeling (fiber content, origin, care) may be required for Saudi import. UNVERIFIED, confirm with a customs broker.",
        "Children's clothing may need extra conformity documentation. UNVERIFIED, flag to the team.",
    ],
)


# --- Shared pieces for non-garment markets ------------------------------------------

def _dimensions(id: str, prompt: str, prompt_ar: str, example: str, example_ar: str) -> Question:
    return Question(id=id, prompt=prompt, prompt_ar=prompt_ar, type="text",
                    hint=f"In centimetres, e.g. {example}", hint_ar=f"بالسنتيمتر، مثال: {example_ar}")


def _quantity(prompt: str, prompt_ar: str, hint: Optional[str] = None, hint_ar: Optional[str] = None) -> Question:
    return Question(id=QUANTITY_ID, prompt=prompt, prompt_ar=prompt_ar, type="number", section="quantity",
                    hint=hint, hint_ar=hint_ar)


def _artwork(hint: str, hint_ar: str) -> Question:
    return Question(id="artwork", prompt="Upload your logo or artwork.", prompt_ar="ارفع شعارك أو التصميم.",
                    type="file", required=False, brand="logo", hint=hint, hint_ar=hint_ar)


_SAMPLE_FIRST = choice(
    "sample", "Do you want a sample before full production?", "هل تريد عينة قبل الإنتاج الكامل؟",
    [("yes, sample first", "نعم، عينة أولًا"), ("no, go straight to production", "لا، مباشرة للإنتاج"),
     ("not sure", "غير متأكد")],
    section="quality", allow_other=False,
    hint="A sample takes about 1-2 weeks and lets you check the product before the full order.",
    hint_ar="العينة تستغرق أسبوعًا إلى أسبوعين تقريبًا، وتتيح لك فحص المنتج قبل الطلب الكامل.",
)


def _custom_option() -> Option:
    return Option(
        id=CUSTOM_OPTION, name="Something else (custom)", name_ar="شيء آخر (مخصص)", uses_common_questions=False,
        questions=[
            Question(id="description", prompt="Describe what you want to make", prompt_ar="صف ما تريد صنعه",
                     type="text", multiline=True,
                     hint="What is it, what is it for, materials, colours, size, logo... write as much as you know.",
                     hint_ar="ما هو، ولماذا، والخامات، والألوان، والمقاس، والشعار... اكتب كل ما تعرفه."),
            Question(id="reference_images", prompt="Add pictures or sketches", prompt_ar="أضف صورًا أو رسومات",
                     type="file", required=False,
                     hint="A photo of a similar product or your own sketch helps a lot.",
                     hint_ar="صورة لمنتج مشابه أو رسمة منك تساعد كثيرًا."),
            _quantity("How many pieces?", "كم قطعة؟"),
            _NEEDED_BY,
        ],
    )


# --- E-commerce packaging ---------------------------------------------------------
# Online sellers' branded packaging: boxes, mailers, tissue, tape, stickers, inserts.

_PRINT_COLORS = choice(
    "print_colors", "How many colours does the print use?", "كم لونًا في الطباعة؟",
    [("one colour (your logo only)", "لون واحد (الشعار فقط)", 1), ("two colours", "لونان", 1),
     ("full colour (CMYK)", "ألوان كاملة (CMYK)", 2), ("foil or special ink", "رقائق ذهبية/فضية أو حبر خاص", 3),
     ("no print", "بدون طباعة")],
    hint="Fewer ink colours cost less. Under Other you can give a Pantone code.",
    hint_ar="كلما قلّت ألوان الطباعة قلّت التكلفة. في «أخرى» يمكنك كتابة رمز Pantone.",
)

_PKG_FIRST_BOX = [
    choice("box_style", "Box style?", "نوع الصندوق؟",
           [("mailer box (folds from one piece, tuck lid)", "صندوق بريدي (قطعة واحدة بغطاء مدمج)", 2),
            ("shipping carton (regular slotted)", "كرتونة شحن عادية", 1),
            ("two-piece box (separate lid and base)", "علبة بغطاء وقاعدة منفصلين", 3)]),
    _dimensions("box_dimensions", "Inside size: length x width x height?", "المقاس الداخلي: الطول × العرض × الارتفاع؟",
                "30 x 22 x 8", "30 × 22 × 8"),
    choice("board", "Board strength?", "سماكة الكرتون؟",
           [("E-flute (thin, about 1.5 mm)", "E-flute (رقيق، نحو 1.5 مم)", 1),
            ("B-flute (about 3 mm)", "B-flute (نحو 3 مم)", 2),
            ("double wall BC (heavy or fragile items)", "طبقتان BC (للأغراض الثقيلة أو الهشة)", 3)],
           hint="E-flute suits clothes and light items. Choose double wall for glass or electronics.",
           hint_ar="E-flute مناسب للملابس والأغراض الخفيفة. اختر الطبقتين للزجاج والإلكترونيات."),
    choice("outside_surface", "Outside surface?", "السطح الخارجي؟",
           [("kraft brown", "بني كرافت", 1), ("white", "أبيض", 2), ("white coated (best for full-colour print)", "أبيض مطلي (الأفضل للطباعة الملونة)", 2)]),
    choice("inside_print", "Print inside the box too?", "طباعة داخل الصندوق أيضًا؟",
           [("no, plain inside", "لا، الداخل سادة"), ("yes, printed inside", "نعم، مطبوع من الداخل", 2)], allow_other=False),
    choice("box_finish", "Surface finish?", "التشطيب؟",
           [("none (uncoated)", "بدون (غير مطلي)", 1), ("matte lamination", "تغليف مطفي", 2),
            ("gloss lamination", "تغليف لامع", 2), ("water-based varnish", "ورنيش مائي", 1)], required=False),
    choice("box_features", "Extras?", "إضافات؟",
           [("tear strip", "شريط فتح"), ("self-adhesive strip", "شريط لاصق ذاتي"), ("insert or divider", "حاجز داخلي"),
            ("handle holes", "فتحات مقبض"), ("FSC certified paper", "ورق معتمد FSC")], multiple=True, required=False),
    choice("box_load", "What will it carry?", "ماذا سيحمل؟",
           [("light (clothes, accessories)", "خفيف (ملابس وإكسسوارات)"), ("medium (up to about 8 kg)", "متوسط (حتى نحو 8 كغ)"),
            ("fragile or heavy (glass, electronics)", "هش أو ثقيل (زجاج، إلكترونيات)")]),
]

_PKG_FIRST_MAILER = [
    _dimensions("mailer_dimensions", "Bag size: width x length (flap not included)?",
                "مقاس الكيس: العرض × الطول (بدون اللسان)؟", "25 x 35", "25 × 35"),
    choice("mailer_material", "Material?", "الخامة؟",
           [("co-extruded polyethylene (opaque)", "بولي إيثيلين متعدد الطبقات (غير شفاف)", 1),
            ("recycled polyethylene", "بولي إيثيلين معاد تدويره", 2),
            ("compostable (PLA + PBAT)", "قابل للتحلل (PLA + PBAT)", 3),
            ("padded bubble mailer", "كيس بفقاعات هوائية", 2)]),
    choice("thickness", "Thickness?", "السماكة؟",
           [("thin (about 40 micron)", "رقيق (نحو 40 ميكرون)", 1), ("standard (about 60 micron)", "عادي (نحو 60 ميكرون)", 2),
            ("strong (about 80 micron)", "قوي (نحو 80 ميكرون)", 3)]),
    choice("item_color", "Bag colour?", "لون الكيس؟",
           [("white", "أبيض"), ("black", "أسود"), ("grey", "رمادي"), ("pink", "وردي"), ("blue", "أزرق"), ("green", "أخضر")],
           brand="colors"),
    choice("mailer_closure", "Closure?", "الإغلاق؟",
           [("self-adhesive strip", "شريط لاصق ذاتي"), ("double strip (for returns)", "شريطان (للمرتجعات)", 2),
            ("tear strip", "شريط فتح")]),
    choice("print_sides", "Print on?", "الطباعة على؟",
           [("one side", "وجه واحد"), ("both sides", "الوجهين", 2), ("inside too", "ومن الداخل أيضًا", 2)]),
    choice("mailer_features", "Extras?", "إضافات؟",
           [("tamper-evident", "يكشف العبث"), ("waterproof", "مقاوم للماء"), ("grey inner layer (hides contents)", "طبقة داخلية رمادية (تخفي المحتوى)")],
           multiple=True, required=False),
]

_PKG_FIRST_TISSUE = [
    choice("sheet_size", "Sheet size?", "مقاس الورقة؟",
           [("50 x 70 cm", "50 × 70 سم"), ("50 x 75 cm", "50 × 75 سم"), ("70 x 100 cm", "70 × 100 سم")]),
    choice("tissue_gsm", "Paper weight?", "وزن الورق؟",
           [("17 gsm (standard)", "17 غرام (عادي)", 1), ("22 gsm (thicker)", "22 غرام (أسمك)", 2),
            ("28 gsm (premium)", "28 غرام (فاخر)", 3)]),
    choice("item_color", "Paper colour?", "لون الورق؟",
           [("white", "أبيض"), ("black", "أسود"), ("kraft brown", "بني كرافت"), ("pink", "وردي"), ("gold", "ذهبي")],
           brand="colors"),
    choice("tissue_print", "Print layout?", "نمط الطباعة؟",
           [("logo repeated all over", "الشعار متكرر على كامل الورقة"), ("one large logo per sheet", "شعار كبير واحد لكل ورقة"),
            ("plain, no print", "سادة بدون طباعة")]),
    choice("tissue_finish", "Finish?", "التشطيب؟",
           [("plain", "عادي"), ("waxed (grease-proof)", "مشمّع (مقاوم للدهون)", 2), ("metallic foil", "رقائق معدنية", 3)],
           required=False),
    choice("food_contact", "Will it touch food?", "هل سيلامس الطعام؟",
           [("no", "لا"), ("yes (food-grade needed)", "نعم (يلزم درجة غذائية)")], allow_other=False,
           hint="Food contact needs food-grade paper and inks, which limits the options.",
           hint_ar="ملامسة الطعام تتطلب ورقًا وأحبارًا بدرجة غذائية، وهذا يقلّل الخيارات."),
]

_PKG_FIRST_GIFT = [
    choice("gift_style", "Box style?", "نوع العلبة؟",
           [("lid and base", "غطاء وقاعدة", 2), ("magnetic flap (book style)", "غطاء مغناطيسي (كتاب)", 3),
            ("drawer with sleeve", "درج مع غلاف", 3), ("foldable rigid box", "علبة صلبة قابلة للطي", 2)]),
    _dimensions("box_dimensions", "Inside size: length x width x height?", "المقاس الداخلي: الطول × العرض × الارتفاع؟",
                "20 x 15 x 6", "20 × 15 × 6"),
    choice("board_thickness", "Board thickness?", "سماكة الكرتون الصلب؟",
           [("1.5 mm", "1.5 مم", 1), ("2 mm (standard)", "2 مم (عادي)", 2), ("3 mm (extra rigid)", "3 مم (صلب جدًا)", 3)]),
    choice("wrap_paper", "Outside paper?", "الورق الخارجي؟",
           [("matte art paper", "ورق فني مطفي", 1), ("textured linen paper", "ورق كتان محبّب", 2),
            ("velvet or soft-touch", "مخمل أو ناعم الملمس", 3), ("kraft", "كرافت", 1)]),
    choice("item_color", "Main colour?", "اللون الأساسي؟",
           [("black", "أسود"), ("white", "أبيض"), ("navy", "كحلي"), ("gold", "ذهبي"), ("pink", "وردي")], brand="colors"),
    choice("gift_insert", "Inside?", "الداخل؟",
           [("empty", "فارغ"), ("paperboard tray", "صينية ورقية", 1), ("EVA foam cut to fit", "إسفنج EVA مقصوص", 2),
            ("satin or ribbon lining", "بطانة ساتان أو شريط", 3)], required=False),
    choice("gift_finish", "Special finishing?", "تشطيب خاص؟",
           [("hot foil logo", "شعار بالرقائق الساخنة", 3), ("emboss or deboss", "نقش بارز أو غائر", 3),
            ("spot UV", "ورنيش موضعي", 2), ("none", "بدون")], multiple=True, required=False),
    choice("gift_ribbon", "Ribbon pull or handle?", "شريط أو مقبض؟",
           [("no", "لا"), ("ribbon pull", "شريط سحب"), ("ribbon handle", "مقبض شريط")], required=False),
]

_PKG_FIRST_TAPE = [
    choice("tape_width", "Tape width?", "عرض الشريط؟",
           [("48 mm (standard)", "48 مم (عادي)"), ("60 mm", "60 مم"), ("72 mm (wide)", "72 مم (عريض)")]),
    choice("tape_length", "Roll length?", "طول اللفة؟",
           [("50 m", "50 متر"), ("100 m", "100 متر"), ("150 m", "150 متر")]),
    choice("tape_thickness", "Thickness?", "السماكة؟",
           [("40 micron", "40 ميكرون", 1), ("48 micron (standard)", "48 ميكرون (عادي)", 2), ("60 micron (strong)", "60 ميكرون (قوي)", 3)]),
    choice("item_color", "Tape colour?", "لون الشريط؟",
           [("clear", "شفاف"), ("white", "أبيض"), ("brown", "بني"), ("black", "أسود")], brand="colors"),
    choice("tape_features", "Extras?", "إضافات؟",
           [("tamper-evident (shows a mark if opened)", "يكشف العبث (يظهر أثر عند الفتح)", 2),
            ("easy hand-tear", "يُقطع باليد بسهولة")], multiple=True, required=False),
]

_PKG_FIRST_STICKER = [
    choice("sticker_shape", "Shape?", "الشكل؟",
           [("circle", "دائرة"), ("square", "مربع"), ("rectangle", "مستطيل"), ("custom die-cut", "قصّ مخصص", 2)]),
    _dimensions("sticker_size", "Size (width x height, or diameter)?", "المقاس (العرض × الارتفاع أو القطر)؟",
                "5 x 5", "5 × 5"),
    choice("sticker_material", "Material?", "الخامة؟",
           [("matte paper", "ورق مطفي", 1), ("glossy paper", "ورق لامع", 1), ("kraft paper", "ورق كرافت", 1),
            ("waterproof vinyl", "فينيل مقاوم للماء", 2), ("clear (transparent)", "شفاف", 2)]),
    choice("sticker_format", "Supplied as?", "كيف تُسلَّم؟",
           [("rolls", "رولات"), ("sheets", "ورقات")]),
    choice("sticker_finish", "Finish?", "التشطيب؟",
           [("none", "بدون"), ("matte lamination", "تغليف مطفي", 1), ("gloss lamination", "تغليف لامع", 1)], required=False),
    choice("sticker_use", "What are they for?", "فيمَ تُستخدم؟",
           [("sealing boxes or bags", "إغلاق الصناديق أو الأكياس"), ("product labels", "ملصقات منتجات"),
            ("thank-you stickers", "ملصقات شكر")]),
]

_PKG_FIRST_CARD = [
    choice("card_size", "Card size?", "مقاس البطاقة؟",
           [("business card 9 x 5.4 cm", "بطاقة عمل 9 × 5.4 سم"), ("A6 (10.5 x 14.8 cm)", "A6 (10.5 × 14.8 سم)"),
            ("A5 (14.8 x 21 cm)", "A5 (14.8 × 21 سم)")]),
    choice("card_paper", "Paper?", "الورق؟",
           [("300 gsm art card", "كرتون فني 300 غرام", 1), ("350 gsm thick card", "كرتون سميك 350 غرام", 2),
            ("kraft card", "كرتون كرافت", 1), ("recycled card", "كرتون معاد تدويره", 2)]),
    choice("card_sides", "Print on?", "الطباعة على؟",
           [("one side", "وجه واحد"), ("both sides", "الوجهين", 2)]),
    choice("card_finish", "Finish?", "التشطيب؟",
           [("uncoated", "بدون تغليف", 1), ("matte lamination", "تغليف مطفي", 2), ("gloss lamination", "تغليف لامع", 2),
            ("spot UV or foil", "ورنيش موضعي أو رقائق", 3)], required=False),
    choice("card_fold", "Fold?", "الطي؟", [("flat", "مسطحة"), ("folded in half", "مطوية إلى نصفين")], required=False),
]

PACKAGING = Market(
    id="ecom_packaging",
    name="E-commerce packaging tools",
    name_ar="أدوات تغليف المتاجر الإلكترونية",
    common_questions=[
        _PRINT_COLORS,
        _artwork("PNG, JPG, SVG, PDF, AI or EPS, up to 10 MB. Vector files (SVG, AI, EPS, PDF) print best.",
                 "PNG أو JPG أو SVG أو PDF أو AI أو EPS، حتى 10 ميغابايت. الملفات المتجهة أفضل للطباعة."),
        _NEEDED_BY,
        Question(
            id="quantity_tiers", prompt="Other quantities you would like to compare (optional)",
            prompt_ar="كميات أخرى تريد مقارنتها (اختياري)", type="text", section="quantity", required=False,
            hint="Packaging gets cheaper per piece in larger runs, e.g. 1000, 3000, 5000.",
            hint_ar="سعر القطعة ينخفض مع الكميات الأكبر، مثال: 1000 و3000 و5000.",
        ),
        choice(
            "carton_packing", "How should they be packed for shipping?", "كيف تُعبّأ للشحن؟",
            [("standard export cartons", "كراتين تصدير عادية", 1), ("flat-packed (folded flat)", "مسطحة (مطوية)", 1),
             ("bundled in 50s or 100s", "حزم من 50 أو 100 قطعة", 1)],
            section="quality", required=False,
        ),
        _SAMPLE_FIRST,
    ],
    options={
        "shipping_box": Option(id="shipping_box", name="Shipping or mailer box", name_ar="صندوق شحن",
                               first_questions=_PKG_FIRST_BOX,
                               questions=[_quantity("How many boxes?", "كم صندوقًا؟")]),
        "poly_mailer": Option(id="poly_mailer", name="Poly mailer bag", name_ar="كيس شحن بلاستيكي",
                              first_questions=_PKG_FIRST_MAILER,
                              questions=[_quantity("How many bags?", "كم كيسًا؟")]),
        "tissue_paper": Option(id="tissue_paper", name="Tissue paper", name_ar="ورق مناديل للتغليف",
                               first_questions=_PKG_FIRST_TISSUE,
                               questions=[_quantity("How many sheets?", "كم ورقة؟")]),
        "gift_box": Option(id="gift_box", name="Rigid gift box", name_ar="علبة هدايا صلبة",
                           first_questions=_PKG_FIRST_GIFT,
                           questions=[_quantity("How many boxes?", "كم علبة؟")]),
        "packing_tape": Option(id="packing_tape", name="Branded packing tape", name_ar="شريط تغليف بشعارك",
                               first_questions=_PKG_FIRST_TAPE,
                               questions=[_quantity("How many rolls?", "كم لفة؟")]),
        "stickers": Option(id="stickers", name="Stickers and labels", name_ar="ملصقات",
                           first_questions=_PKG_FIRST_STICKER,
                           questions=[_quantity("How many stickers?", "كم ملصقًا؟")]),
        "thank_you_cards": Option(id="thank_you_cards", name="Thank-you cards and inserts", name_ar="بطاقات شكر وإدراجات",
                                  first_questions=_PKG_FIRST_CARD,
                                  questions=[_quantity("How many cards?", "كم بطاقة؟")]),
        CUSTOM_OPTION: _custom_option(),
    },
    compliance_notes=[
        "Packaging that touches food needs food-grade material and inks. UNVERIFIED for Saudi import, flag to the team.",
        "Compostable or biodegradable claims may need certification. UNVERIFIED, flag to the team.",
    ],
)


# --- Tech accessories --------------------------------------------------------------
# Cases, laptop bags and mouse pads: made for a device or a desk, so sizes and device models matter most.

_TECH_COMMON = [
    choice(
        "colors", "Main colours?", "ما الألوان الأساسية؟",
        [("black", "أسود"), ("white", "أبيض"), ("navy", "كحلي"), ("grey", "رمادي"), ("clear", "شفاف"), ("pink", "وردي")],
        multiple=True, brand="colors",
        hint="Under Other you can add a Pantone or HEX code.", hint_ar="في «أخرى» يمكنك إضافة رمز اللون (Pantone أو HEX).",
    ),
    choice(
        "decoration_method", "How should the logo/design be applied?", "كيف يُطبَّق الشعار أو التصميم؟",
        [("UV print", "طباعة UV", 2), ("silk screen print", "طباعة حرير", 1), ("dye-sublimation (full colour)", "طباعة حرارية كاملة الألوان", 2),
         ("laser engraving", "نقش بالليزر", 2), ("embroidery", "تطريز", 3), ("debossed or embossed", "نقش غائر أو بارز", 2),
         ("no logo", "بدون شعار")],
        hint="Not every method works on every material; the factory will confirm.",
        hint_ar="ليست كل طريقة مناسبة لكل خامة، وسيؤكد المصنع.",
    ),
    _artwork("PNG, JPG, SVG, PDF, AI or EPS, up to 10 MB. Vector files (SVG, AI, EPS, PDF) work best.",
             "PNG أو JPG أو SVG أو PDF أو AI أو EPS، حتى 10 ميغابايت. الملفات المتجهة (SVG وAI وEPS وPDF) هي الأفضل."),
    choice("logo_area", "Where should the design go?", "أين يوضع التصميم؟",
           [("centred", "في المنتصف"), ("lower corner", "في الزاوية السفلية"), ("all over (full print)", "على كامل السطح"),
            ("back side only", "الخلف فقط")], required=False),
    _NEEDED_BY,
    choice(
        "retail_packaging", "How should each piece be packed?", "كيف تُغلَّف كل قطعة؟",
        [("individual polybag", "كيس بلاستيكي لكل قطعة", 1), ("retail box with your branding", "علبة بيع بشعارك", 3),
         ("hang card with polybag", "بطاقة تعليق مع كيس", 2), ("bulk, no individual packing", "بالجملة دون تغليف فردي", 1)],
        section="quality", multiple=True,
    ),
    _SAMPLE_FIRST,
]

_TECH_FIRST_CASE = [
    Question(id="device_models", prompt="Which device models?", prompt_ar="لأي أجهزة؟", type="text",
             hint="Exact models, e.g. iPhone 16 Pro, Galaxy S25. A case made for the wrong model does not fit.",
             hint_ar="الموديلات بدقة، مثال: iPhone 16 Pro وGalaxy S25. الغطاء الخاطئ لن يناسب الجهاز."),
    choice("case_material", "Material?", "الخامة؟",
           [("liquid silicone", "سيليكون سائل", 2), ("clear TPU", "TPU شفاف", 1), ("hard polycarbonate (PC)", "بولي كربونات صلب", 1),
            ("PC + TPU hybrid", "هجين PC + TPU", 2), ("PU leather", "جلد صناعي", 2),
            ("biodegradable (wheat straw / PLA)", "قابل للتحلل (قش القمح / PLA)", 3)]),
    choice("case_finish", "Surface feel?", "ملمس السطح؟",
           [("matte", "مطفي"), ("glossy", "لامع"), ("soft touch", "ناعم الملمس", 2), ("frosted clear", "شفاف مصنفر")]),
    choice("case_features", "Features?", "المزايا؟",
           [("MagSafe magnets", "مغناطيس MagSafe", 3), ("raised camera protection", "حماية بارزة للكاميرا"),
            ("shockproof corners", "زوايا ماصة للصدمات", 2), ("anti-yellowing", "مقاوم للاصفرار", 2),
            ("card slot", "جيب بطاقات", 2)], multiple=True, required=False),
]

_TECH_FIRST_LAPTOP = [
    choice("bag_type", "Type?", "النوع؟",
           [("sleeve (slides in)", "غطاء (ينزلق فيه الجهاز)", 1), ("messenger bag", "حقيبة كتف", 2),
            ("backpack", "حقيبة ظهر", 3), ("briefcase", "حقيبة عمل", 3)]),
    choice("laptop_size", "Laptop sizes?", "مقاسات اللابتوب؟",
           [("13 inch", "13 بوصة"), ("14 inch", "14 بوصة"), ("15.6 inch", "15.6 بوصة"), ("16-17 inch", "16-17 بوصة")],
           multiple=True, hint="Pick every size you need; each size is a separate pattern.",
           hint_ar="اختر كل المقاسات المطلوبة، لكل مقاس نمط منفصل."),
    choice("bag_material", "Outer material?", "الخامة الخارجية؟",
           [("neoprene", "نيوبرين", 1), ("polyester", "بوليستر", 1), ("nylon", "نايلون", 2), ("PU leather", "جلد صناعي", 2),
            ("canvas", "كانفاس", 2), ("felt", "لباد", 1), ("recycled PET", "بوليستر معاد تدويره", 2)]),
    choice("padding", "Padding?", "الحشوة؟",
           [("none", "بدون", 1), ("light foam", "إسفنج خفيف", 1), ("thick protective foam", "إسفنج حماية سميك", 2)]),
    choice("bag_closure", "Closure?", "الإغلاق؟",
           [("zipper", "سحّاب"), ("flap with velcro", "لسان بفيلكرو"), ("magnetic flap", "لسان مغناطيسي", 2)]),
    choice("bag_pockets", "Pockets?", "الجيوب؟",
           [("front accessory pocket", "جيب أمامي للإكسسوارات"), ("inner pocket", "جيب داخلي"), ("no pockets", "بدون جيوب")],
           multiple=True, required=False),
    choice("bag_carry", "Carrying?", "الحمل؟",
           [("none", "بدون"), ("handle", "مقبض"), ("detachable shoulder strap", "حزام كتف قابل للفك")], required=False),
    choice("bag_features", "Features?", "المزايا؟",
           [("water-resistant", "مقاوم للماء", 2), ("shock-absorbing", "ماص للصدمات", 2),
            ("hidden anti-theft pocket", "جيب مخفي ضد السرقة", 2), ("trolley strap", "حزام للحقيبة المتحركة", 1)],
           multiple=True, required=False),
]

_TECH_FIRST_MOUSEPAD = [
    choice("pad_size", "Size?", "المقاس؟",
           [("standard 22 x 18 cm", "عادي 22 × 18 سم", 1), ("large 30 x 25 cm", "كبير 30 × 25 سم", 1),
            ("desk mat 80 x 30 cm", "لوح مكتب 80 × 30 سم", 2), ("XL desk mat 90 x 40 cm", "لوح مكتب كبير 90 × 40 سم", 3),
            ("XXL 100 x 50 cm", "ضخم 100 × 50 سم", 3)],
           hint="Under Other: width x length in cm.", hint_ar="في «أخرى»: العرض × الطول بالسنتيمتر."),
    choice("pad_thickness", "Thickness?", "السماكة؟",
           [("2 mm", "2 مم", 1), ("3 mm (standard)", "3 مم (عادي)", 1), ("4 mm", "4 مم", 2), ("5 mm", "5 مم", 3)]),
    choice("pad_surface", "Top surface?", "السطح العلوي؟",
           [("speed cloth (smooth, fast)", "قماش سريع (ناعم)", 1), ("control cloth (more grip)", "قماش تحكّم (احتكاك أكثر)", 1),
            ("full-colour sublimation cloth", "قماش طباعة كاملة الألوان", 2), ("PU leather", "جلد صناعي", 2)]),
    choice("pad_base", "Base?", "القاعدة؟",
           [("natural rubber (non-slip)", "مطاط طبيعي (مانع للانزلاق)", 2), ("recycled rubber", "مطاط معاد تدويره", 1)]),
    choice("pad_edge", "Edge?", "الحافة؟",
           [("stitched edge (lasts longer)", "حافة مخيطة (تدوم أكثر)", 2), ("cut edge (no stitching)", "حافة مقصوصة (بدون خياطة)", 1)]),
    choice("pad_shape", "Shape?", "الشكل؟",
           [("rectangle", "مستطيل"), ("round", "دائري"), ("custom die-cut shape", "شكل مخصص", 2),
            ("with wrist rest", "مع مسند معصم", 2)]),
    choice("pad_features", "Extras?", "إضافات؟",
           [("RGB lighting", "إضاءة RGB", 3), ("wireless charging", "شحن لاسلكي", 3), ("waterproof", "مقاوم للماء", 1)],
           multiple=True, required=False,
           hint="Powered pads may need extra safety approval to import.",
           hint_ar="اللوحات الكهربائية قد تحتاج موافقة سلامة إضافية للاستيراد."),
]

TECH = Market(
    id="tech_accessories",
    name="Tech accessories",
    name_ar="الإكسسوارات التقنية",
    common_questions=_TECH_COMMON,
    options={
        "phone_case": Option(
            id="phone_case", name="Phone case", name_ar="غطاء جوال", first_questions=_TECH_FIRST_CASE,
            questions=[
                _quantity("How many cases in total?", "كم غطاءً بالمجموع؟"),
                Question(id="model_quantities", prompt="How many of each model?", prompt_ar="كم قطعة لكل موديل؟",
                         type="text", section="quantity", hint="e.g. iPhone 16 Pro: 200, Galaxy S25: 100",
                         hint_ar="مثال: iPhone 16 Pro: 200، Galaxy S25: 100"),
            ],
        ),
        "laptop_bag": Option(
            id="laptop_bag", name="Laptop bag or sleeve", name_ar="حقيبة لابتوب", first_questions=_TECH_FIRST_LAPTOP,
            questions=[_quantity("How many bags in total?", "كم حقيبة بالمجموع؟")],
        ),
        "mouse_pad": Option(
            id="mouse_pad", name="Mouse pad or desk mat", name_ar="لوح ماوس", first_questions=_TECH_FIRST_MOUSEPAD,
            questions=[_quantity("How many pads?", "كم لوحًا؟")],
        ),
        CUSTOM_OPTION: _custom_option(),
    },
    compliance_notes=[
        "Products with batteries, lights or wireless charging may need Saudi (SASO) approval. UNVERIFIED, flag to the team.",
        "Branded devices' cases (Apple, Samsung) may raise trademark questions. UNVERIFIED, flag to the team.",
    ],
)


MARKETS: dict[str, Market] = {m.id: m for m in [APPAREL, PACKAGING, TECH]}


def get_questions(market_id: str, option_id: str) -> list[Question]:
    market = MARKETS[market_id]
    option = market.options[option_id]
    common = market.common_questions if option.uses_common_questions else []
    chart = SIZE_CHARTS.get(option.id)

    # Placement questions draw this product's garment; size questions carry its size chart
    def specialise(q: Question) -> Question:
        if q.type == "placement" and option.mockup:
            return q.model_copy(update={"mockup": option.mockup})
        if q.type == "color_zones" and option.mockup:
            return q.model_copy(update={"mockup": option.mockup, "zones": zones_for(option.mockup)})
        if q.type == "size_table" and chart:
            return q.model_copy(update={"size_chart": chart})
        return q

    return [specialise(q) for q in option.first_questions + common + option.questions]
