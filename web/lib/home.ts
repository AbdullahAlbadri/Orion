// Landing page copy, Arabic and English (docs/website/landing-redesign.md). Edit wording here.
// Rules: no invented prices, statistics, testimonials, timelines or photos; undecided items stay out.
// Orion does not offer customs clearance: say nothing that implies it (one honest FAQ line only).
import type { Lang } from "./i18n";

export type T = Record<Lang, string>;
const t = (ar: string, en: string): T => ({ ar, en });

export const HOME = {
  nav: {
    how: t("كيف نعمل", "How it works"),
    markets: t("المجالات", "Markets"),
    costs: t("التكلفة", "Costs"),
    faq: t("الأسئلة", "FAQ"),
    signIn: t("تسجيل الدخول", "Sign in"),
    dashboard: t("لوحتي", "My dashboard"),
    start: t("ابدأ طلبك", "Start your order"),
    menu: t("القائمة", "Menu"),
    close: t("إغلاق", "Close"),
    skip: t("انتقل إلى المحتوى", "Skip to content"),
  },
  hero: {
    kicker: t("فكرتك ← المصنع ← بابك", "IDEA → FACTORY → YOUR DOOR"),
    words: t("الشبكة الوحيدة بين فكرتك ومصنعك", "The only network between your idea and your factory"),
    accent: t("فكرتك", "idea"),            // the word drawn in gold
    // The route drawing: where your idea starts and where factories are. Labels only, no claims.
    from: t("فكرتك · السعودية", "Your idea · Saudi Arabia"),
    to: t("المصنع · الصين", "The factory · China"),
    sub: t(
      "صف منتجك للمساعد الذكي، وراجع ملخصًا واضحًا، ونتولى التواصل مع المصنع والشحن إلى عنوانك.",
      "Describe your product to our AI assistant, review a clear summary, and we handle the factory and shipping to your address.",
    ),
    secondary: t("كيف نعمل", "How it works"),
  },
  // The hero mock-up: an illustration, labelled as such. TODO(decide): final wording.
  demo: {
    label: t("مثال توضيحي", "Illustrative example"),
    replay: t("إعادة التشغيل", "Replay"),
    assistant: t("مساعد أوريون", "Orion assistant"),
    customer: t("أبغى أصنع هودي بشعار شركتي", "I want to make hoodies with my company logo"),
    reply: t("ممتاز! أي خامة تفضّل؟", "Great! Which fabric would you like?"),
    chips: [t("قطن 280 جم", "Cotton 280 gsm"), t("قطن 350 جم", "Cotton 350 gsm"), t("بوليستر", "Polyester")],
    specTitle: t("ملخص منتجك", "Your product summary"),
    rows: [
      { label: t("الخامة", "Fabric"), value: t("قطن 280 جم", "Cotton 280 gsm") },
      { label: t("المقاس", "Size"), value: t("L", "L") },
      { label: t("الكمية", "Quantity"), value: t("200", "200") },
      { label: t("اللون", "Colour"), value: t("أسود", "Black") },
    ],
    ready: t("ملخصك جاهز", "Your summary is ready"),
    editHint: t("اضغط على أي قيمة لتعديلها", "Tap any value to edit it"),
  },
  strip: [t("هودي", "Hoodies"), t("عباية", "Abayas"), t("دفتر تخطيط", "Planners"), t("غطاء وسادة", "Pillow covers"),
    t("قلادة حيوانات", "Pet collars"), t("كيس شحن", "Mailer bags"), t("زي موحد", "Uniforms"), t("حقيبة قماشية", "Tote bags")],
  why: {
    num: "01",
    title: t("شبكة مصانع تعمل لصالحك", "A factory network that works for you"),
    visualCaption: t("أنت تتحدث مع جهة واحدة، ونحن نتحدث مع المصانع", "You talk to one contact; we talk to the factories"),
    you: t("أنت", "You"),
    factory: t("المصانع", "Factories"),
    points: [
      { title: t("جهة اتصال واحدة", "One point of contact"),
        text: t("بدل مراسلة عشرات المصانع، تتحدث معنا فقط.", "Instead of messaging dozens of factories, you only talk to us.") },
      { title: t("لا شيء ينقص", "Nothing missing"),
        text: t("المساعد يسأل ما يسأله المصنع، ويقارن كل رد بطلبك.", "The assistant asks what a factory would ask, and checks every reply against your order.") },
      { title: t("كل خطوة مرئية", "Every step visible"),
        text: t("ملخص قبل الطلب، وعرض سعر واضح، وصور وتحديثات، وتتبع للشحنة.", "A summary before you order, a clear quote, photos and updates, and shipment tracking.") },
      { title: t("منتجاتك محفوظة", "Your products are saved"),
        text: t("أعد الطلب بضغطة دون إعادة الأسئلة.", "Reorder in one click without answering the questions again.") },
    ],
  },
  how: {
    num: "02",
    title: t("من فكرتك إلى مستودعك في أربع خطوات", "From your idea to your warehouse in four steps"),
    steps: [
      { title: t("صف فكرتك", "Describe your idea"),
        text: t("المساعد يسألك عن التفاصيل ويقبل صورك وملفاتك.", "The assistant asks about the details and takes your pictures and files.") },
      { title: t("راجع ملخصك", "Review your summary"),
        text: t("ترى منتجك كاملًا قبل أن يُرسل لأي مصنع.", "See your whole product before it goes to any factory.") },
      { title: t("وافق على العرض والعينة", "Approve the quote and sample"),
        text: t("يصلك عرض السعر، وتقرر متى تكمل.", "Your quote arrives, and you decide when to go ahead.") },
      { title: t("تابع كل شيء", "Follow everything"),
        text: t("إنتاج وشحن وتحديثات بالصور في مكان واحد.", "Production, shipping and photo updates in one place.") },
    ],
    // Labels inside the illustrated screens
    screens: {
      summary: t("ملخص منتجك", "Your product summary"),
      design: t("التصميم", "Design"), quantity: t("الكمية", "Quantity"), quality: t("الجودة", "Quality"),
      logo: t("الشعار", "Logo"), logoValue: t("تطريز، يسار الصدر", "Embroidery, left chest"),
      sizes: t("المقاسات", "Sizes"), fabric: t("الخامة", "Fabric"),
      confirm: t("تأكيد وإرسال للمصانع", "Confirm and send to factories"),
      quote: t("عرض السعر", "Your quote"),
      approve: t("موافقة", "Approve"), sample: t("أطلب عينة أولًا", "Sample first"),
      timeline: t("طلبك", "Your order"),
      stages: [t("تجهيز الطلب", "Preparing your order"), t("مع المصنع", "With the factory"), t("عرض السعر", "Quote"),
        t("قيد التصنيع", "In production"), t("في الطريق", "On its way"), t("تم التسليم", "Delivered")],
      update: t("تحديث جديد من المصنع مع صور", "New factory update with photos"),
    },
    // The paper trail: one document per stop, the same order code on each
    trail: {
      code: t("مسار الطلب · ٤ محطات", "ORDER ROUTE · 4 STOPS"),
      stop: t("محطة", "STOP"),
      from: t("من", "From"), to: t("إلى", "To"),
      idea: t("فكرتك", "Your idea"), assistant: t("المساعد", "The assistant"), summary: t("ملخصك", "Your summary"),
      factory: t("المصنع", "The factory"), decision: t("قرارك", "Your decision"), door: t("بابك", "Your door"),
      product: t("المنتج", "Product"), productValue: t("هودي", "Hoodie"), sampleRow: t("العينة", "Sample"),
      sampleValue: t("أولًا", "First"), status: t("الحالة", "Status"), waiting: t("بانتظار موافقتك", "Waiting for you"),
      done: t("تم", "Done"), approved: t("موافق", "Approved"), onTheWay: t("في الطريق", "On its way"),
    },
  },
  markets: {
    num: "03",
    title: t("ماذا نصنع لك؟", "What can we make for you?"),
    live: t("متاح الآن", "Available now"),
    soon: t("يفتح قريبًا", "Opening soon"),
    more: t("التفاصيل", "Details"),
    options: t("المنتجات", "Products"),
    asked: t("ما سنسألك عنه", "What you'll be asked"),
    startHere: t("ابدأ طلبًا في هذا المجال", "Start an order in this market"),
    soonNote: t("نجهّز هذا المجال الآن.", "We're preparing this market now."),
    items: [
      {
        id: "apparel", live: true, icon: "shirt",
        name: t("الأزياء والملابس والزي الموحد", "Apparel & uniforms"),
        examples: [t("هودي", "Hoodie"), t("عباية", "Abaya"), t("زي موحد", "Uniform")],
        options: t("هودي، تيشيرت واسع، عباية، حقيبة قماشية، زي موحد، منتج مخصص",
          "Hoodie, oversized T-shirt, abaya, tote bag, corporate uniform, custom"),
        asked: t("القماش ووزنه، الكمية لكل مقاس، الألوان، طريقة الشعار وموضعه، الملصقات، التغليف",
          "Fabric and weight, pieces per size, colours, logo method and placement, labels, packaging"),
      },
      {
        id: "stationery", live: false, icon: "book",
        name: t("القرطاسية والمنتجات الورقية", "Stationery & paper goods"),
        examples: [t("مخطط يومي", "Planner"), t("دفتر", "Notebook"), t("ملصقات", "Stickers")],
        options: t("مخطط يومي، دفتر، لباد مكتب، ملصقات، منتج مخصص", "Daily planner, notebook, desk mat, stickers, custom"),
        asked: t("المقاسات، عدد الصفحات، نوع الورق ووزنه، التجليد، تشطيب الغلاف، ألوان الطباعة، التخطيط العربي والتاريخ الهجري/الميلادي",
          "Dimensions, pages, paper type and weight, binding, cover finish, print colours, Arabic layout and Hijri/Gregorian dates"),
      },
      {
        id: "home_textiles", live: false, icon: "layers",
        name: t("المنسوجات المنزلية", "Home textiles"),
        examples: [t("مفارش سرير", "Bed sheets"), t("أكياس وسائد", "Pillow covers"), t("سجادات صلاة", "Prayer mats")],
        options: t("مفارش سرير، أكياس وسائد، سجادات صلاة، مناشف، منتج مخصص", "Bed sheets, pillow covers, prayer mats, towels, custom"),
        asked: t("المقاس، القماش وكثافة الخيط، الألوان والنقشة، الطباعة أو النسج، التشطيب، التغليف",
          "Size, fabric and thread count, colours and pattern, print or weave, finish, packaging"),
      },
      {
        id: "tech_soft_goods", live: false, icon: "sparkle",
        name: t("الإكسسوارات التقنية ونمط الحياة", "Tech & lifestyle accessories"),
        examples: [t("غطاء جوال", "Phone case"), t("حقيبة لابتوب", "Laptop sleeve"), t("لباد ماوس", "Mousepad")],
        options: t("غطاء جوال سيليكون، حقيبة لابتوب، لباد ماوس، سوار ساعة، منتج مخصص", "Silicone phone case, laptop sleeve, mousepad, watch band, custom"),
        asked: t("موديل الجهاز أو عرض السوار، الخامة، اللون، التشطيب، طريقة الشعار، السماكة، الإغلاق",
          "Device model or band width, material, colour, finish, logo method, thickness, closure"),
      },
      {
        id: "pet", live: false, icon: "heart",
        name: t("مستلزمات الحيوانات الأليفة (غير غذائية)", "Pet accessories (non-food)"),
        examples: [t("سرير", "Pet bed"), t("طوق", "Collar"), t("لعبة مضغ", "Chew toy")],
        options: t("سرير، مقود، طوق، لعبة مضغ، منتج مخصص", "Pet bed, leash, collar, chew toy, custom"),
        asked: t("مقاس الحيوان، الخامة، القطع المعدنية، قوة التحمل، سلامة خامات ألعاب المضغ، الألوان",
          "Pet size range, material, hardware, strength, chew-toy material safety, colours"),
      },
      {
        id: "packaging", live: false, icon: "box",
        name: t("تغليف المتاجر الإلكترونية", "Branded e-commerce packaging"),
        examples: [t("أكياس شحن", "Mailer bags"), t("صناديق", "Boxes"), t("ورق مناديل", "Tissue paper")],
        options: t("ورق مناديل، أكياس شحن، صناديق كرتون، منتج مخصص", "Tissue paper, poly mailers, corrugated boxes, custom"),
        asked: t("المقاسات، الخامة والسماكة، ألوان الطباعة، الإغلاق، فئات الكمية، الاستخدام للأغذية أو القطع الهشة",
          "Dimensions, material and thickness, print colours, closure, quantity tiers, food or fragile use"),
      },
    ],
  },
  costs: {
    num: "04",
    title: t("مم تتكون التكلفة؟", "What does it cost?"),
    parts: [
      { title: t("تكلفة المنتج", "Product cost"), text: t("سعر المصنع لمنتجك وكميتك.", "The factory's price for your product and quantity.") },
      // TODO(decide): fee model
      { title: t("رسوم أوريون", "Orion fee"), text: t("رسوم خدمتنا، واضحة في عرض السعر.", "Our service fee, shown clearly in your quote.") },
      // TODO(decide): shipping method and who books it
      { title: t("الشحن", "Shipping"), text: t("من المصنع إلى عنوانك.", "From the factory to your address.") },
    ],
    receipt: {
      title: t("عرض السعر", "Quote"),
      total: t("الإجمالي", "Total"),
      caption: t("هكذا يظهر عرض السعر قبل أن تؤكد", "This is how your quote looks before you confirm"),
    },
    promises: [
      t("ترى كل التكاليف قبل أن تؤكد.", "You see every cost before you confirm."),
      t("الأسعار تأتي من المصانع، وفريقنا هو من يتولى الاتفاق عليها. الذكاء الاصطناعي لا يتفاوض على الأسعار.",
        "Prices come from factories, and our team handles agreeing them. The AI never negotiates prices."),
      t("لا أسعار تقديرية.", "No estimated prices."),
    ],
  },
  people: {
    num: "05",
    title: t("وراء أوريون فريق حقيقي", "A real team behind Orion"),
    // TODO(decide): team portraits, names and roles once each person agrees
    commitments: [
      { icon: "lock", title: t("ملفاتك خاصة", "Your files stay private"),
        text: t("شعارك وصورك لا يراها إلا أنت وفريقنا والمصنع الذي ينفّذ طلبك.",
          "Your logo and pictures are seen only by you, our team and the factory making your order.") },
      { icon: "check", title: t("كل شيء قبل التأكيد", "Everything before you confirm"),
        text: t("مواصفات كاملة ثم تكاليف كاملة قبل أي التزام.", "The full specification, then every cost, before you commit to anything.") },
      { icon: "people", title: t("فريق بشري خلف الذكاء الاصطناعي", "People behind the AI"),
        text: t("أي سؤال عن السعر أو التغيير يراجعه فريقنا.", "Any question about price or changes is reviewed by our team.") },
    ],
  },
  faq: {
    num: "06",
    title: t("أسئلتك، وأجوبتنا", "Your questions, our answers"),
    // Only questions the team has answered. TODO(decide): payment, samples
    groups: [
      {
        id: "order", name: t("الطلب", "Ordering"),
        items: [
          { id: "what", q: t("ما هو أوريون؟", "What is Orion?"),
            a: t("وسيط بين صاحب المشروع والمصانع. تصف منتجك، ونحن نتواصل مع المصنع ونتابع التصنيع والشحن إلى عنوانك.",
              "A middle-man between business owners and factories. You describe your product; we deal with the factory and follow production and shipping to your address.") },
          { id: "files", q: t("هل يمكنني رفع صور وملفات؟", "Can I upload pictures and files?"),
            a: t("نعم. ارفع شعارك ليظهر على رسم المنتج، أو صورًا ورسومات لمنتج مخصص؛ المساعد ينظر إليها ليسألك عن التفاصيل الناقصة.",
              "Yes. Upload your logo to see it on the product drawing, or pictures and sketches for a custom product; the assistant looks at them to ask about missing details.") },
          { id: "summary", q: t("ما هو الملخص قبل الطلب؟", "What is the summary before ordering?"),
            a: t("ملخص كامل لمنتجك (بدون أسعار) تراجعه وتؤكده قبل أن نرسله إلى أي مصنع. بعد التأكيد يُحفظ كما هو.",
              "A full summary of your product (without prices) that you review and confirm before it goes to any factory. Once confirmed it is saved exactly as it is.") },
          { id: "follow", q: t("كيف أتابع طلبي؟", "How do I follow my order?"),
            a: t("من لوحتك: ترى مرحلة كل طلب وما ينتظره منك.", "From your dashboard: you see each order's stage and anything waiting for you.") },
        ],
      },
      {
        id: "costs", name: t("التكلفة", "Costs"),
        items: [
          { id: "cost", q: t("مم تتكون التكلفة؟", "What is the cost made of?"),
            a: t("تكلفة المنتج من المصنع، ورسوم أوريون، والشحن إلى عنوانك. تظهر كلها في عرض السعر.",
              "The factory's product cost, Orion's fee and shipping to your address. All of them are in your quote.") },
          { id: "before", q: t("هل أرى كل التكاليف قبل التأكيد؟", "Do I see every cost before I confirm?"),
            a: t("نعم. لا تلتزم بشيء قبل أن ترى عرض السعر كاملًا.", "Yes. You don't commit to anything before you see the full quote.") },
          { id: "ai-price", q: t("هل يتفاوض الذكاء الاصطناعي على السعر؟", "Does the AI negotiate the price?"),
            a: t("لا. الذكاء الاصطناعي لا يناقش الأسعار؛ الأسعار تأتي من المصانع وفريقنا هو من يتولى الاتفاق عليها.",
              "No. The AI never discusses prices; prices come from factories and our team handles agreeing them.") },
        ],
      },
      {
        id: "shipping", name: t("الشحن", "Shipping"),
        items: [
          { id: "who", q: t("من يتولى الشحن؟", "Who handles shipping?"),
            a: t("نحن. نشحن طلبك من المصنع إلى عنوانك.", "We do. We ship your order from the factory to your address.") },
          { id: "customs", q: t("هل تتولون التخليص الجمركي؟", "Do you handle customs clearance?"),
            a: t("لا، أوريون لا يقدّم خدمة التخليص الجمركي.", "No, Orion does not offer customs clearance.") },
        ],
      },
      {
        id: "privacy", name: t("الخصوصية", "Privacy"),
        items: [
          { id: "data", q: t("من يرى ملفاتي وبياناتي؟", "Who sees my files and data?"),
            a: t("أنت وفريقنا، والمصنع الذي ينفّذ طلبك يرى ما يحتاجه لصنعه فقط.",
              "You and our team; the factory making your order sees only what it needs to make it.") },
        ],
      },
    ],
    privacyLink: t("الشروط والخصوصية", "Terms and privacy"),
  },
  closing: {
    lines: [t("هذه نهاية الصفحة.", "This is the end of the page."), t("بداية منتجك من هنا.", "Your product starts here.")],
  },
  footer: {
    legal: t("الشروط والخصوصية", "Terms & privacy"),
    rights: t("© أوريون", "© Orion"),
  },
  legal: {
    title: t("الشروط والخصوصية", "Terms and privacy"),
    note: t("نُعدّ هذه الشروط مع مستشار قانوني، وستُنشر قبل قبول أي مدفوعات.",
      "We are preparing these terms with a lawyer. They will be published before any payment is taken."),
    sections: [t("شروط الاستخدام", "Terms of use"), t("سياسة الخصوصية", "Privacy policy"),
      t("الاسترجاع والإلغاء", "Refunds and cancellations"), t("المنتجات الممنوعة", "Restricted products"),
      t("الملكية الفكرية", "Intellectual property")],
  },
};
