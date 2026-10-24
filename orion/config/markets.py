"""Market registry. Markets and options are config; the graph never hardcodes them.

Add a new market by defining a Market and registering it in MARKETS.
"""

from pydantic import BaseModel

from orion.spec import QUANTITY_ID, SIZE_TABLE_ID, Question

CUSTOM_OPTION = "custom"


class Option(BaseModel):
    id: str
    name: str
    questions: list[Question] = []
    uses_common_questions: bool = True


class Market(BaseModel):
    id: str
    name: str
    name_ar: str
    common_questions: list[Question]
    options: dict[str, Option]
    # Saudi import rules are UNVERIFIED; anything here is flagged to the team, never quoted blindly.
    compliance_notes: list[str] = []


# --- Fashion, apparel & uniforms -------------------------------------------------

_SIZE_TABLE = Question(
    id=SIZE_TABLE_ID,
    prompt="How many pieces per size?",
    type="size_table",
    hint="e.g. S:20, M:50, L:50, XL:30",
)
_LABELS = Question(
    id="labels",
    prompt="Which labels do you need?",
    type="text",
    hint="e.g. woven neck label with logo, size label, care label, hang tag",
)
_FIT_REFERENCE = Question(
    id="fit_reference",
    prompt="Do you have a fit reference (a garment or brand whose fit you like)?",
    type="text",
    required=False,
)
_FABRIC_GSM = Question(
    id="fabric_gsm",
    prompt="Fabric weight in GSM (grams per square metre)?",
    type="number",
    hint="T-shirts are usually 160-240, hoodies 280-400. Say if you are unsure.",
)


def _fabric(*choices: str) -> Question:
    return Question(id="fabric", prompt="Which fabric?", type="choice", choices=[*choices, "other"])


APPAREL = Market(
    id="apparel",
    name="Fashion, apparel & uniforms",
    name_ar="الأزياء والملابس والزي الموحد",
    common_questions=[
        Question(
            id="colors",
            prompt="Garment colors? Include color codes (Pantone/HEX) if you have them.",
            type="text",
        ),
        Question(
            id="decoration_method",
            prompt="How should the logo/design be applied?",
            type="choice",
            choices=["screen print", "DTG print", "embroidery", "heat transfer", "none", "other"],
        ),
        Question(
            id="decoration_placement",
            prompt="Where does the design go, and how big?",
            type="text",
            hint="e.g. left chest 8cm, full back 30cm",
        ),
        Question(
            id="artwork",
            prompt="Upload or link your logo/artwork.",
            type="file",
            required=False,
        ),
    ],
    options={
        "hoodie": Option(
            id="hoodie",
            name="Hoodie",
            questions=[
                _fabric("cotton fleece", "cotton-poly fleece", "french terry"),
                _FABRIC_GSM,
                Question(id="hoodie_style", prompt="Pullover or zip-up?", type="choice", choices=["pullover", "zip-up"]),
                _SIZE_TABLE,
                _LABELS,
                _FIT_REFERENCE,
            ],
        ),
        "oversized_tee": Option(
            id="oversized_tee",
            name="Oversized T-shirt",
            questions=[
                _fabric("100% cotton", "cotton-poly", "heavyweight cotton"),
                _FABRIC_GSM,
                Question(id="neckline", prompt="Neckline?", type="choice", choices=["crew neck", "mock neck", "v-neck"]),
                _SIZE_TABLE,
                _LABELS,
                _FIT_REFERENCE,
            ],
        ),
        "abaya": Option(
            id="abaya",
            name="Abaya",
            questions=[
                _fabric("crepe", "nida", "linen", "chiffon"),
                Question(
                    id="abaya_length",
                    prompt="Abaya length per size (cm)?",
                    type="text",
                    hint="e.g. 52: 132cm, 54: 137cm, 56: 142cm",
                ),
                Question(
                    id="sleeve_style",
                    prompt="Sleeve style?",
                    type="choice",
                    choices=["straight", "wide/bisht", "cuffed", "other"],
                ),
                Question(id="embellishment", prompt="Any embellishment (embroidery, beading, lace, trims)?", type="text"),
                _SIZE_TABLE,
                _LABELS,
            ],
        ),
        "tote_bag": Option(
            id="tote_bag",
            name="Tote bag",
            questions=[
                _fabric("cotton canvas", "cotton", "non-woven", "jute"),
                Question(id="dimensions", prompt="Bag dimensions (width x height x gusset, cm)?", type="text"),
                Question(id="handle_length", prompt="Handle length (cm)?", type="number"),
                Question(id=QUANTITY_ID, prompt="How many bags?", type="number"),
            ],
        ),
        "corporate_uniform": Option(
            id="corporate_uniform",
            name="Corporate uniform",
            questions=[
                Question(id="garment_type", prompt="Which garments (polo, shirt, trousers, jacket...)?", type="text"),
                _fabric("cotton", "poly-cotton", "polyester", "gabardine"),
                Question(
                    id="logo_placement",
                    prompt="Where does the company logo go on each garment?",
                    type="text",
                ),
                Question(
                    id=SIZE_TABLE_ID,
                    prompt="Staff count per size?",
                    type="size_table",
                    hint="e.g. S:5, M:12, L:10, XL:4",
                ),
                _LABELS,
            ],
        ),
        CUSTOM_OPTION: Option(id=CUSTOM_OPTION, name="Something else (custom)", uses_common_questions=False),
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
    return common + option.questions
