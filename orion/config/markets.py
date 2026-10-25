"""Market registry. Markets and options are config; the graph never hardcodes them.

Add a new market by defining a Market and registering it in MARKETS. Every question has English and Arabic
wording; answers are stored with the English choice values whatever language the customer uses.
"""

from typing import Optional

from pydantic import BaseModel

from orion.config.size_charts import SIZE_CHARTS
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
_FIT = choice(
    "fit_reference", "Which fit do you want?", "ما القَصّة التي تريدها؟",
    [("regular fit", "قصة عادية"), ("relaxed fit", "قصة مريحة"), ("oversized", "واسعة (أوفر سايز)"),
     ("slim fit", "ضيقة")],
    required=False,
    hint="Under Other you can name a garment or brand whose fit you like.",
    hint_ar="في «أخرى» يمكنك ذكر قطعة أو علامة تعجبك قصّتها.",
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


def _fabric(*options: tuple[str, str]) -> Question:
    return choice("fabric", "Which fabric?", "ما نوع القماش؟", list(options), section="quality")


# The product's own attributes, asked before everything else (the customer's checklist for a hoodie)
_HOODIE_FIRST = [
    choice("logo_position", "Logo position?", "موضع الشعار؟",
           [("front", "الأمام"), ("back", "الخلف"), ("left sleeve", "الكم الأيسر"), ("right sleeve", "الكم الأيمن"),
            ("hood", "القلنسوة"), ("no logo", "بدون شعار")], multiple=True),
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
    choice("gender", "Gender?", "الفئة؟", [("unisex", "للجنسين"), ("men", "رجالي"), ("women", "نسائي"), ("kids", "أطفال")]),
    choice("season", "Season?", "الموسم؟",
           [("winter", "الشتاء"), ("autumn", "الخريف"), ("spring", "الربيع"), ("summer", "الصيف"),
            ("all seasons", "كل المواسم")], multiple=True, required=False),
    choice("supply_type", "Supply type?", "نوع التوريد؟",
           [("OEM service", "تصنيع بتصميمك وشعارك (OEM)"), ("ODM service", "تصميم المصنع مع شعارك (ODM)"),
            ("ready stock with your logo", "منتج جاهز مع شعارك")],
           hint="OEM: the factory makes your own design. ODM: you pick one of the factory's designs and add your brand.",
           hint_ar="OEM: يصنع المصنع تصميمك أنت. ODM: تختار من تصاميم المصنع وتضيف علامتك."),
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
            hint="Tap a spot or add a logo, then drag it into place and drag the corner to resize.",
            hint_ar="اختر موضعًا أو أضف شعارًا، ثم اسحبه إلى مكانه واسحب الزاوية لتغيير الحجم.",
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
            questions=[
                _fabric(("100% cotton", "قطن 100%", 2), ("cotton-poly", "قطن وبوليستر", 1),
                        ("heavyweight cotton", "قطن ثقيل", 3)),
                _FABRIC_GSM,
                choice("neckline", "Neckline?", "شكل الياقة؟",
                       [("crew neck", "ياقة دائرية"), ("mock neck", "ياقة مرتفعة"), ("v-neck", "ياقة V")]),
                _size_table(),
                _SIZE_STANDARD,
                _LABELS,
                _FIT,
            ],
        ),
        "abaya": Option(
            id="abaya", name="Abaya", name_ar="عباية", mockup="abaya",
            questions=[
                _fabric(("crepe", "كريب", 2), ("nida", "ندى", 3), ("linen", "كتان", 2), ("chiffon", "شيفون", 2)),
                Question(
                    id="abaya_length", prompt="Abaya length per size (cm)?", prompt_ar="طول العباية لكل مقاس (سم)؟",
                    type="text", section="quantity",
                    hint="e.g. 52: 132cm, 54: 137cm, 56: 142cm", hint_ar="مثال: 52: 132 سم، 54: 137 سم، 56: 142 سم",
                ),
                choice("sleeve_style", "Sleeve style?", "شكل الأكمام؟",
                       [("straight", "مستقيمة"), ("wide/bisht", "واسعة (بشت)"), ("cuffed", "بأساور")]),
                choice("embellishment", "Any embellishment?", "هل تريد زخرفة؟",
                       [("none", "بدون"), ("embroidery", "تطريز", 2), ("beading", "خرز", 3), ("lace", "دانتيل", 2),
                        ("trims", "شرائط وزينة", 1)], multiple=True),
                _size_table(),
                _LABELS,
            ],
        ),
        "tote_bag": Option(
            id="tote_bag", name="Tote bag", name_ar="حقيبة قماشية", mockup="tote",
            questions=[
                _fabric(("cotton canvas", "كانفاس قطني", 2), ("cotton", "قطن", 1), ("non-woven", "قماش غير منسوج", 1),
                        ("jute", "جوت", 2)),
                choice("dimensions", "Bag size?", "مقاس الحقيبة؟",
                       [("small 30x35cm", "صغيرة 30×35 سم"), ("standard 38x42cm", "عادية 38×42 سم"),
                        ("large 40x45x10cm", "كبيرة 40×45×10 سم")],
                       hint="Under Other: width x height x gusset in cm.",
                       hint_ar="في «أخرى»: العرض × الارتفاع × العمق بالسنتيمتر."),
                Question(id="handle_length", prompt="Handle length (cm)?", prompt_ar="طول المقبض (سم)؟", type="number"),
                Question(id=QUANTITY_ID, prompt="How many bags?", prompt_ar="كم حقيبة؟", type="number",
                         section="quantity"),
            ],
        ),
        "corporate_uniform": Option(
            id="corporate_uniform", name="Corporate uniform", name_ar="زي موحد للشركات", mockup="polo",
            questions=[
                choice("garment_type", "Which garments?", "ما القطع المطلوبة؟",
                       [("polo shirt", "قميص بولو"), ("dress shirt", "قميص رسمي"), ("t-shirt", "تيشيرت"),
                        ("trousers", "بنطال"), ("jacket", "جاكيت"), ("cap", "قبعة")], multiple=True),
                _fabric(("cotton", "قطن", 2), ("poly-cotton", "بولي قطن", 1), ("polyester", "بوليستر", 1),
                        ("gabardine", "جبردين", 3)),
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


MARKETS: dict[str, Market] = {m.id: m for m in [APPAREL]}


def get_questions(market_id: str, option_id: str) -> list[Question]:
    market = MARKETS[market_id]
    option = market.options[option_id]
    common = market.common_questions if option.uses_common_questions else []
    chart = SIZE_CHARTS.get(option.id)

    # Placement questions draw this product's garment; size questions carry its size chart
    def specialise(q: Question) -> Question:
        if q.type == "placement" and option.mockup:
            return q.model_copy(update={"mockup": option.mockup})
        if q.type == "size_table" and chart:
            return q.model_copy(update={"size_chart": chart})
        return q

    return [specialise(q) for q in option.first_questions + common + option.questions]
