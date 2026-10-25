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
# Choice questions offer common answers; allow_other lets the customer type their own ("Other"),
# multiple lets them pick several.

_SIZE_TABLE = Question(
    id=SIZE_TABLE_ID,
    prompt="How many pieces per size?",
    type="size_table",
    hint="e.g. S:20, M:50, L:50, XL:30",
    section="quantity",
)
_LABELS = Question(
    id="labels",
    prompt="Which labels do you need?",
    type="choice",
    choices=["woven neck label with logo", "printed neck label", "size label", "care label", "hang tag", "no labels"],
    multiple=True,
    allow_other=True,
    section="quality",
)
_FIT = Question(
    id="fit_reference",
    prompt="Which fit do you want?",
    type="choice",
    choices=["regular fit", "relaxed fit", "oversized", "slim fit"],
    allow_other=True,
    required=False,
    hint="Under Other you can name a garment or brand whose fit you like.",
)
_FABRIC_GSM = Question(
    id="fabric_gsm",
    prompt="Fabric weight in GSM (grams per square metre)?",
    type="number",
    hint="T-shirts are usually 160-240, hoodies 280-400. Ask Orion if you are unsure.",
    section="quality",
)


def _fabric(*choices: str) -> Question:
    return Question(
        id="fabric", prompt="Which fabric?", type="choice", choices=list(choices), allow_other=True, section="quality",
    )


APPAREL = Market(
    id="apparel",
    name="Fashion, apparel & uniforms",
    name_ar="الأزياء والملابس والزي الموحد",
    common_questions=[
        Question(
            id="colors",
            prompt="Garment colors?",
            type="choice",
            choices=["black", "white", "navy", "grey", "beige", "olive"],
            multiple=True,
            allow_other=True,
            hint="Under Other you can add a Pantone or HEX code.",
        ),
        Question(
            id="decoration_method",
            prompt="How should the logo/design be applied?",
            type="choice",
            choices=["screen print", "DTG print", "embroidery", "heat transfer", "no logo"],
            allow_other=True,
        ),
        Question(
            id="decoration_placement",
            prompt="Where does the design go?",
            type="choice",
            choices=["left chest", "center chest", "full front", "full back", "sleeve", "back neck"],
            multiple=True,
            allow_other=True,
            hint="Under Other you can add sizes, e.g. left chest 8cm.",
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
                _FIT,
            ],
        ),
        "oversized_tee": Option(
            id="oversized_tee",
            name="Oversized T-shirt",
            questions=[
                _fabric("100% cotton", "cotton-poly", "heavyweight cotton"),
                _FABRIC_GSM,
                Question(id="neckline", prompt="Neckline?", type="choice", choices=["crew neck", "mock neck", "v-neck"],
                         allow_other=True),
                _SIZE_TABLE,
                _LABELS,
                _FIT,
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
                    section="quantity",
                ),
                Question(
                    id="sleeve_style",
                    prompt="Sleeve style?",
                    type="choice",
                    choices=["straight", "wide/bisht", "cuffed"],
                    allow_other=True,
                ),
                Question(
                    id="embellishment",
                    prompt="Any embellishment?",
                    type="choice",
                    choices=["none", "embroidery", "beading", "lace", "trims"],
                    multiple=True,
                    allow_other=True,
                ),
                _SIZE_TABLE,
                _LABELS,
            ],
        ),
        "tote_bag": Option(
            id="tote_bag",
            name="Tote bag",
            questions=[
                _fabric("cotton canvas", "cotton", "non-woven", "jute"),
                Question(
                    id="dimensions",
                    prompt="Bag size?",
                    type="choice",
                    choices=["small 30x35cm", "standard 38x42cm", "large 40x45x10cm"],
                    allow_other=True,
                    hint="Under Other: width x height x gusset in cm.",
                ),
                Question(id="handle_length", prompt="Handle length (cm)?", type="number"),
                Question(id=QUANTITY_ID, prompt="How many bags?", type="number", section="quantity"),
            ],
        ),
        "corporate_uniform": Option(
            id="corporate_uniform",
            name="Corporate uniform",
            questions=[
                Question(
                    id="garment_type",
                    prompt="Which garments?",
                    type="choice",
                    choices=["polo shirt", "dress shirt", "t-shirt", "trousers", "jacket", "cap"],
                    multiple=True,
                    allow_other=True,
                ),
                _fabric("cotton", "poly-cotton", "polyester", "gabardine"),
                Question(
                    id="logo_placement",
                    prompt="Where does the company logo go?",
                    type="choice",
                    choices=["left chest", "right chest", "sleeve", "back", "cap front"],
                    multiple=True,
                    allow_other=True,
                ),
                Question(
                    id=SIZE_TABLE_ID,
                    prompt="Staff count per size?",
                    type="size_table",
                    hint="e.g. S:5, M:12, L:10, XL:4",
                    section="quantity",
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
