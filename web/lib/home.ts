// Home page copy, Arabic and English (docs/website/01-home.md). Edit wording here.
// Rule: no invented prices, statistics, testimonials or timelines. Undecided items stay out.
import type { Lang } from "./i18n";

type T = Record<Lang, string>;
const t = (ar: string, en: string): T => ({ ar, en });

export const HOME = {
  nav: {
    how: t("كيف نعمل", "How it works"),
    markets: t("المجالات", "Markets"),
    pricing: t("التكلفة", "Pricing"),
    faq: t("الأسئلة الشائعة", "FAQ"),
    trust: t("لماذا أوريون", "Why Orion"),
    signIn: t("تسجيل الدخول", "Sign in"),
    dashboard: t("لوحتي", "My dashboard"),
    start: t("ابدأ طلبك", "Start your order"),
  },
  hero: {
    title: t("الشبكة الوحيدة بين فكرتك ومصنعك", "The only network between your idea and your factory"),
    sub: t(
      "صف منتجك، ونتولى المصنع والشحن والأوراق الجمركية. أنت ركّز على نمو مشروعك.",
      "Describe your product, and we handle the factory, shipping and customs paperwork. You focus on growing your business.",
    ),
    secondary: t("كيف نعمل", "See how it works"),
  },
  problem: {
    title: t("لماذا يصعب التصنيع اليوم؟", "Why is manufacturing hard today?"),
    items: [
      {
        title: t("لا شبكة مصانع", "No factory network"),
        text: t("أغلب أصحاب المشاريع الجدد لا يعرفون أين يجدون مصنعًا موثوقًا يقبل طلبهم.",
          "Most new business owners don't know where to find a reliable factory that will take their order."),
      },
      {
        title: t("عشرات التفاصيل الدقيقة", "Dozens of exact details"),
        text: t("المصنع يحتاج القماش والوزن والمقاسات والألوان والتغليف قبل أن يعطيك سعرًا.",
          "A factory needs fabric, weight, sizes, colours and packaging before it can give you a price."),
      },
      {
        title: t("الشحن والجمارك", "Shipping and customs"),
        text: t("منتج جيد قد يتعطّل عند الشحن أو الأوراق الجمركية.",
          "A good product can still get stuck in shipping or customs paperwork."),
      },
    ],
  },
  how: {
    title: t("كيف نعمل", "How it works"),
    steps: [
      { title: t("صف فكرتك", "Describe your idea"), text: t("أجب عن أسئلة بسيطة، وارفع شعارك أو صورًا. الذكاء الاصطناعي يسأل عن كل ما يحتاجه المصنع.", "Answer simple questions and upload your logo or pictures. Our AI asks everything a factory needs.") },
      { title: t("راجع ملخصك", "Review your pre-receipt"), text: t("ترى منتجك كاملًا في ملخص واضح قبل أن نرسله لأي مصنع.", "See your whole product in a clear summary before it goes to any factory.") },
      { title: t("وافق على العرض والعينة", "Approve the quote and sample"), text: t("نعرض عليك عرض السعر من المصنع، وتقرر متى تكمل.", "We show you the factory's quote, and you decide when to go ahead.") },
      { title: t("نتابع كل شيء عنك", "We manage the rest"), text: t("نتابع التصنيع والشحن والجمارك، وأنت تتابع كل خطوة من لوحتك.", "We manage production, shipping and customs; you follow every step from your dashboard.") },
    ],
  },
  markets: {
    title: t("المجالات", "Markets"),
    sub: t("اختر مجالًا لترى المنتجات وما سنسألك عنه.", "Pick a market to see the products and what we'll ask you."),
    live: t("متاح الآن", "Available now"),
    soon: t("قريبًا", "Coming soon"),
    options: t("المنتجات", "Products"),
    asked: t("ما سنسألك عنه", "What you'll be asked"),
    startHere: t("ابدأ طلبًا في هذا المجال", "Start an order in this market"),
    soonNote: t("نجهّز هذا المجال الآن.", "We're preparing this market now."),
    items: [
      {
        id: "apparel", live: true, icon: "shirt",
        name: t("الأزياء والملابس والزي الموحد", "Apparel & uniforms"),
        options: t("هودي، تيشيرت واسع، عباية، حقيبة قماشية، زي موحد، منتج مخصص",
          "Hoodie, oversized T-shirt, abaya, tote bag, corporate uniform, custom"),
        asked: t("القماش ووزنه، الكمية لكل مقاس، الألوان، طريقة الشعار وموضعه، الملصقات، التغليف",
          "Fabric and weight, pieces per size, colours, logo method and placement, labels, packaging"),
      },
      {
        id: "stationery", live: false, icon: "book",
        name: t("القرطاسية والمنتجات الورقية", "Stationery & paper goods"),
        options: t("مخطط يومي، دفتر، لباد مكتب، ملصقات، منتج مخصص", "Daily planner, notebook, desk mat, stickers, custom"),
        asked: t("المقاسات، عدد الصفحات، نوع الورق ووزنه، التجليد، تشطيب الغلاف، ألوان الطباعة، التخطيط العربي والتاريخ الهجري/الميلادي",
          "Dimensions, pages, paper type and weight, binding, cover finish, print colours, Arabic layout and Hijri/Gregorian dates"),
      },
      {
        id: "home_textiles", live: false, icon: "layers",
        name: t("المنسوجات المنزلية", "Home textiles"),
        options: t("مفارش سرير، أكياس وسائد، سجادات صلاة، مناشف، منتج مخصص", "Bed sheets, pillow covers, prayer mats, towels, custom"),
        asked: t("المقاس، القماش وكثافة الخيط، الألوان والنقشة، الطباعة أو النسج، التشطيب، التغليف",
          "Size, fabric and thread count, colours and pattern, print or weave, finish, packaging"),
      },
      {
        id: "tech_soft_goods", live: false, icon: "sparkle",
        name: t("الإكسسوارات التقنية ونمط الحياة", "Tech & lifestyle accessories"),
        options: t("غطاء جوال سيليكون، حقيبة لابتوب، لباد ماوس، سوار ساعة، منتج مخصص", "Silicone phone case, laptop sleeve, mousepad, watch band, custom"),
        asked: t("موديل الجهاز أو عرض السوار، الخامة، اللون، التشطيب، طريقة الشعار، السماكة، الإغلاق",
          "Device model or band width, material, colour, finish, logo method, thickness, closure"),
      },
      {
        id: "pet", live: false, icon: "heart",
        name: t("مستلزمات الحيوانات الأليفة (غير غذائية)", "Pet accessories (non-food)"),
        options: t("سرير، مقود، طوق، لعبة مضغ، منتج مخصص", "Pet bed, leash, collar, chew toy, custom"),
        asked: t("مقاس الحيوان، الخامة، القطع المعدنية، قوة التحمل، سلامة خامات ألعاب المضغ، الألوان",
          "Pet size range, material, hardware, strength, chew-toy material safety, colours"),
      },
      {
        id: "packaging", live: false, icon: "box",
        name: t("تغليف المتاجر الإلكترونية", "Branded e-commerce packaging"),
        options: t("ورق مناديل، أكياس شحن، صناديق كرتون، منتج مخصص", "Tissue paper, poly mailers, corrugated boxes, custom"),
        asked: t("المقاسات، الخامة والسماكة، ألوان الطباعة، الإغلاق، فئات الكمية، الاستخدام للأغذية أو القطع الهشة",
          "Dimensions, material and thickness, print colours, closure, quantity tiers, food or fragile use"),
      },
    ],
  },
  pricing: {
    title: t("ممّ تتكوّن التكلفة؟", "What your total is made of"),
    parts: [
      { title: t("تكلفة المنتج", "Product cost"), text: t("سعر المصنع لمنتجك.", "The factory's price for your product.") },
      { title: t("رسوم أوريون", "Orion fee"), text: t("رسوم خدمتنا، واضحة في عرض السعر.", "Our service fee, shown clearly in your quote.") },
      { title: t("الشحن", "Shipping"), text: t("من المصنع إلى عنوانك.", "From the factory to your address.") },
      { title: t("الجمارك والرسوم", "Customs and duties"), text: t("رسوم الاستيراد عند الوصول.", "Import duties on arrival.") },
    ],
    promises: [
      t("ترى كل التكاليف قبل أن تؤكد.", "You see every cost before you confirm."),
      t("الذكاء الاصطناعي لا يتفاوض على الأسعار أبدًا؛ فريقنا يتولى ذلك.", "Our AI never negotiates prices; our team handles that."),
      t("لا أسعار تقديرية: الأسعار تأتي من المصانع فقط.", "No made-up prices: prices only come from factories."),
    ],
  },
  faq: {
    title: t("الأسئلة الشائعة", "Frequently asked questions"),
    items: [
      { q: t("ما هو أوريون؟", "What is Orion?"),
        a: t("وسيط بين صاحب المشروع والمصانع. تصف منتجك، ونحن نتواصل مع المصنع ونتابع التصنيع والشحن والأوراق الجمركية نيابة عنك.",
          "A middle-man between business owners and factories. You describe your product; we deal with the factory and follow production, shipping and customs paperwork for you.") },
      { q: t("هل يمكنني رفع صور؟", "Can I upload photos?"),
        a: t("نعم. ارفع شعارك ليظهر على رسم المنتج، أو صورًا ورسومات لمنتج مخصص؛ الذكاء الاصطناعي يقرأ الصور ليسألك عن التفاصيل الناقصة.",
          "Yes. Upload your logo to see it on the product drawing, or pictures and sketches for a custom product; our AI looks at them to ask about missing details.") },
      { q: t("ما هو الملخص قبل الطلب؟", "What is the pre-receipt?"),
        a: t("ملخص كامل لمنتجك (بدون أسعار) تراجعه وتؤكده قبل أن نرسله إلى أي مصنع. بعد التأكيد يُحفظ كما هو.",
          "A full summary of your product (without prices) that you review and confirm before it goes to any factory. Once confirmed it is saved exactly as it is.") },
      { q: t("كيف أتابع طلبي؟", "How do I follow my order?"),
        a: t("من لوحتك: ترى مرحلة كل طلب وما ينتظره منك.", "From your dashboard: you see each order's stage and anything waiting for you.") },
      { q: t("من يتولى الجمارك؟", "Who handles customs?"),
        a: t("نحن نتولى الأوراق الجمركية مع شركة التخليص نيابة عنك.", "We handle the customs paperwork with the clearance company on your behalf.") },
    ],
  },
  trust: {
    title: t("لماذا تثق بأوريون؟", "Why trust Orion?"),
    items: [
      { title: t("لا تفاوض آلي على الأسعار", "No AI price haggling"), text: t("الأسعار من المصانع فقط، وفريقنا هو من يتواصل بشأنها.", "Prices come only from factories, and our team is the one who discusses them.") },
      { title: t("كل شيء قبل التأكيد", "Everything before you confirm"), text: t("ترى المواصفات كاملة، ثم كل التكاليف، قبل أي التزام.", "You see the full specification, then every cost, before committing to anything.") },
      { title: t("ملفاتك خاصة", "Your files stay private"), text: t("شعارك وصورك لا يراها إلا أنت وفريقنا.", "Your logo and pictures are seen only by you and our team.") },
    ],
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
