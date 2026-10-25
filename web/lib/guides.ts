// Short guides behind the info icon on each order question: what the options mean and when to choose them.
// General product knowledge only: no prices (the real price comes from the factory's quote), relative cost
// at most. Keyed by topic; QUESTION_GUIDES maps a question id from the market config to its topic.
import { t, type T } from "./copy";

export type Guide = { title: T; intro: T; items: { name: T; text: T }[]; tip?: T };

/** Where an option's photo lives (made once by scripts/guide_images.py): /guides/<topic>/<slug of the English name>.webp */
export const guideImage = (topic: string, nameEn: string) =>
  `/guides/${topic}/${nameEn.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "")}.webp`;

export const GUIDES: Record<string, Guide> = {
  materials: {
    title: t("أنواع الخامات", "Types of material"),
    intro: t("الخامة هي الألياف التي يُصنع منها القماش، وتحدد ملمس القطعة ودفأها وتحمّلها للغسيل.",
      "The material is the fibre the fabric is made of. It decides how the piece feels, how warm it is and how it survives washing."),
    items: [
      { name: t("قطن 100%", "100% cotton"), text: t("ناعم ويسمح بالتهوية ومريح على البشرة. قد ينكمش قليلًا إذا لم يُعالج مسبقًا، ويظهر عليه التجعد أكثر.", "Soft, breathable and comfortable on the skin. Can shrink a little unless pre-shrunk, and wrinkles more.") },
      { name: t("قطن وبوليستر 80/20", "Cotton-polyester 80/20"), text: t("أغلب الإحساس قطني مع ثبات أفضل في المقاس والشكل، وانكماش أقل. خيار شائع للهوديز.", "Feels mostly like cotton but holds its size and shape better, with less shrinking. A common choice for hoodies.") },
      { name: t("قطن وبوليستر 60/40", "Cotton-polyester 60/40"), text: t("أمتن وأقل تجعدًا وأسرع جفافًا، وملمسه أقل نعومة قليلًا من القطن.", "Tougher, wrinkles less and dries faster; a little less soft than cotton.") },
      { name: t("بوليستر 100%", "100% polyester"), text: t("خفيف ويحافظ على اللون والشكل ويجف بسرعة، لكنه أقل تهوية. مناسب للملابس الرياضية والطباعة بالتسامي.", "Light, keeps its colour and shape and dries fast, but breathes less. Suits sportswear and sublimation printing.") },
      { name: t("قطن عضوي", "Organic cotton"), text: t("قطن يُزرع دون مبيدات صناعية، مناسب للعلامات التي تهتم بالاستدامة. عادةً أعلى تكلفة.", "Cotton grown without synthetic pesticides, for brands that care about sustainability. Usually costs more.") },
      { name: t("بوليستر معاد تدويره", "Recycled polyester"), text: t("مصنوع من بلاستيك معاد تدويره، بخصائص البوليستر نفسها تقريبًا، ويُسوَّق كخيار صديق للبيئة.", "Made from recycled plastic, with nearly the same properties as polyester; marketed as an eco-friendly option.") },
      { name: t("قطن وسباندكس", "Cotton-spandex"), text: t("قطن مع نسبة صغيرة من الألياف المطاطية يعطي مرونة وتماسكًا في القصّات الضيقة.", "Cotton with a little stretch fibre, for give and shape in fitted cuts.") },
    ],
    tip: t("إن لم تكن متأكدًا، قطن وبوليستر 80/20 توازن جيد بين النعومة والثبات للهوديز.", "Not sure? Cotton-polyester 80/20 is a good balance of softness and durability for hoodies."),
  },
  fabric_types: {
    title: t("أنواع النسيج", "Types of fabric"),
    intro: t("طريقة صناعة القماش (الحياكة أو النسج) تحدد سماكته ومرونته وشكل وجهه الداخلي.", "How the fabric is made (knitted or woven) decides its thickness, stretch and what the inside looks like."),
    items: [
      { name: t("صوف محبوك (فليس)", "Knitted fleece"), text: t("وجهه الداخلي مُمشّط ناعم ودافئ. الأشهر للهوديز الشتوية.", "Brushed, soft and warm on the inside. The classic winter hoodie fabric.") },
      { name: t("فرنش تيري", "French terry"), text: t("من الداخل حلقات صغيرة غير مُمشّطة؛ أخف من الفليس ويسمح بالتهوية، مناسب للربيع والخريف.", "Small unbrushed loops inside; lighter and more breathable than fleece, good for spring and autumn.") },
      { name: t("جيرسي محبوك", "Jersey knit"), text: t("قماش التيشيرتات الناعم المرن، خفيف ومناسب للأجواء الدافئة.", "The soft, stretchy T-shirt fabric; light and good for warm weather.") },
      { name: t("وافل محبوك", "Waffle knit"), text: t("نسيج بمربعات بارزة يعطي ملمسًا مميزًا ومظهرًا عصريًا.", "A raised grid texture with a distinctive feel and modern look.") },
      { name: t("منسوج", "Woven"), text: t("قماش غير مطاطي ومتين مثل قماش الجاكيتات والقمصان، يستخدم لقطع أكثر رسمية.", "A non-stretch, sturdy fabric like jackets and shirts, for more structured pieces.") },
    ],
  },
  printing: {
    title: t("طرق الطباعة والتطريز", "Types of printing and embroidery"),
    intro: t("طريقة تطبيق الشعار تؤثر على شكله وملمسه وتحمّله للغسيل وتكلفته.", "How the logo is applied affects its look, feel, how long it lasts and the cost."),
    items: [
      { name: t("طباعة الشاشة (سلك سكرين)", "Screen print"), text: t("ألوان قوية وتدوم طويلًا، وتكون اقتصادية للكميات الكبيرة. يُفضّل للتصاميم بعدد ألوان قليل.", "Strong, long-lasting colours, economical for larger quantities. Best for designs with few colours.") },
      { name: t("الطباعة الرقمية المباشرة (DTG)", "DTG print"), text: t("طباعة تشبه الطابعة المنزلية على القماش؛ مناسبة للتصاميم الملونة والصور والكميات الصغيرة.", "Prints like an inkjet on fabric; suits colourful designs, photos and small runs.") },
      { name: t("التطريز", "Embroidery"), text: t("خيوط مخيطة على القماش تعطي مظهرًا فاخرًا وتدوم طويلًا. مناسب للشعارات الصغيرة والمتوسطة، وأقل مناسبة للتفاصيل الدقيقة جدًا. عادةً أعلى تكلفة.", "Thread stitched into the fabric: a premium look that lasts. Best for small to medium logos, less for very fine detail. Usually costs more.") },
      { name: t("الطباعة الحرارية", "Heat transfer"), text: t("التصميم يُطبع على ورق خاص ثم يُكبس بالحرارة؛ سريعة ومناسبة للأسماء والأرقام والكميات الصغيرة، وقد تتشقق مع الوقت.", "The design is printed on transfer film and heat-pressed; quick and good for names, numbers and small runs, can crack over time.") },
      { name: t("بدون شعار", "No logo"), text: t("قطعة سادة دون أي طباعة أو تطريز.", "A plain piece with no print or embroidery.") },
    ],
    tip: t("الملفات المتجهة (SVG أو AI أو PDF) تعطي أفضل نتيجة في كل الطرق.", "Vector files (SVG, AI or PDF) give the best result with every method."),
  },
  placement: {
    title: t("مواضع الشعار", "Logo positions"),
    intro: t("مكان الشعار وحجمه يغيّران مظهر القطعة كثيرًا. اليسار واليمين بحسب من يلبس القطعة.", "Where the logo goes and how big it is changes the look a lot. Left and right are the wearer's."),
    items: [
      { name: t("الأمام / يسار الصدر", "Front / left chest"), text: t("شعار صغير (نحو 7–10 سم) فوق القلب؛ مظهر أنيق ومناسب للزي الموحد.", "A small logo (about 7–10 cm) over the heart; neat and good for uniforms.") },
      { name: t("وسط الصدر أو كامل الأمام", "Centre chest or full front"), text: t("شعار أو تصميم كبير يلفت النظر؛ مناسب للعلامات والتصاميم الجريئة.", "A big logo or design that stands out; suits brands and bold designs.") },
      { name: t("الخلف", "Back"), text: t("مساحة كبيرة لتصميم كامل أو شعار أعلى الظهر.", "A large area for a full design, or a small logo at the top of the back.") },
      { name: t("الأكمام", "Sleeves"), text: t("شعار أو كتابة صغيرة على الكم تضيف لمسة مميزة.", "A small logo or text on the sleeve adds a distinctive touch.") },
      { name: t("القلنسوة", "Hood"), text: t("شعار صغير على جانب القلنسوة يظهر عند ارتدائها.", "A small logo on the side of the hood, seen when it is worn up.") },
    ],
  },
  hoodie_types: {
    title: t("أنواع الهودي", "Hoodie types"),
    intro: t("طريقة فتح الهودي من الأمام.", "How the hoodie opens at the front."),
    items: [
      { name: t("بدون سحّاب (Pullover)", "Pullover"), text: t("يُلبس من الرأس، بواجهة كاملة مناسبة للطباعة الكبيرة. الأبسط في التصنيع.", "Goes on over the head, with a full front that suits large prints. Simplest to make.") },
      { name: t("بسحّاب كامل", "Zip-up"), text: t("يُفتح بالكامل من الأمام؛ عملي للبس والخلع، والطباعة الأمامية تنقسم على جانبين.", "Opens fully at the front; easy on and off, but a front print is split in two.") },
      { name: t("بنصف سحّاب", "Half-zip"), text: t("سحّاب قصير من الرقبة؛ مظهر رياضي عصري مع واجهة شبه كاملة للطباعة.", "A short zip from the neck; a sporty, modern look with most of the front free for print.") },
    ],
  },
  collars: {
    title: t("أنواع الياقات", "Collar types"),
    intro: t("شكل فتحة الرقبة أو القلنسوة.", "The shape of the neckline or hood."),
    items: [
      { name: t("بقلنسوة", "Hooded"), text: t("القلنسوة التقليدية بطبقة واحدة.", "The classic single-layer hood.") },
      { name: t("قلنسوة بطبقتين", "Double-layer hood"), text: t("قلنسوة مبطنة أسمك وتحافظ على شكلها؛ مظهر أفخم وأدفأ.", "A lined, thicker hood that keeps its shape; looks more premium and is warmer.") },
      { name: t("ياقة دائرية", "Crew neck"), text: t("بدون قلنسوة، كالسويت شيرت التقليدي.", "No hood, like a classic sweatshirt.") },
      { name: t("ياقة مرتفعة", "Mock neck"), text: t("ياقة قصيرة مرتفعة حول الرقبة.", "A short raised collar around the neck.") },
      { name: t("ياقة عالية واسعة", "Funnel neck"), text: t("ياقة عالية تمتد من القماش نفسه وتغطي الرقبة.", "A tall collar cut from the body fabric that covers the neck.") },
      { name: t("ياقة V", "V-neck"), text: t("فتحة على شكل حرف V، أكثر شيوعًا في التيشيرتات.", "A V-shaped opening, more common on T-shirts.") },
    ],
  },
  fit: {
    title: t("أنواع القصّات", "Fit types"),
    intro: t("مدى اتساع القطعة على الجسم. القصّة تؤثر على المقاس الذي يختاره الزبون.", "How loosely the piece sits on the body. The fit affects which size customers pick."),
    items: [
      { name: t("عادية", "Regular"), text: t("مريحة دون أن تكون ضيقة أو واسعة؛ تناسب أغلب الناس.", "Comfortable, neither tight nor baggy; suits most people.") },
      { name: t("واسعة", "Loose / relaxed"), text: t("أوسع قليلًا من العادية لراحة أكبر.", "A little roomier than regular, for comfort.") },
      { name: t("أوفر سايز", "Oversized"), text: t("واسعة بشكل مقصود مع أكتاف ساقطة غالبًا؛ مظهر ستريت وير.", "Deliberately big, often with dropped shoulders; a streetwear look.") },
      { name: t("مربعة (Boxy)", "Boxy"), text: t("عريضة ومستقيمة وأقصر قليلًا، بشكل مربع.", "Wide, straight and slightly shorter, with a square shape.") },
      { name: t("ضيقة", "Slim"), text: t("قريبة من الجسم؛ تحتاج خامة فيها مرونة غالبًا.", "Close to the body; often needs a fabric with some stretch.") },
    ],
  },
  design_details: {
    title: t("تفاصيل التصميم", "Design details"),
    intro: t("لمسات في قصّ القطعة وخياطتها تعطيها طابعًا خاصًا.", "Touches in the cut and sewing that give the piece its character."),
    items: [
      { name: t("سادة", "Plain"), text: t("بدون أي تفاصيل إضافية.", "No extra details.") },
      { name: t("بفتحات (Cut out)", "Cut out"), text: t("فتحات مقصودة في أماكن محددة لإطلالة جريئة.", "Deliberate openings in chosen places, for a bold look.") },
      { name: t("ممزق (Distressed)", "Distressed"), text: t("مظهر مستعمل بحواف وثقوب مقصودة.", "A worn look with deliberate frays and holes.") },
      { name: t("ألوان متداخلة", "Colour block"), text: t("أجزاء بألوان مختلفة في القطعة نفسها.", "Panels in different colours in one piece.") },
      { name: t("رقع (Patchwork)", "Patchwork"), text: t("قطع قماش مختلفة مخيطة معًا.", "Different fabric pieces sewn together.") },
      { name: t("حافة غير مخيطة", "Raw hem"), text: t("حواف مقصوصة دون ثنية، لمظهر عصري غير رسمي.", "Cut edges left unfolded, for a casual modern look.") },
      { name: t("فتحات جانبية", "Side slits"), text: t("فتحات صغيرة أسفل الجانبين تعطي حرية حركة.", "Small slits at the bottom of the sides for movement.") },
    ],
  },
  length: {
    title: t("أطوال القطعة", "Lengths"),
    intro: t("طول القطعة من الكتف إلى الأسفل.", "How long the piece is from shoulder to hem."),
    items: [
      { name: t("عادي", "Regular"), text: t("يصل إلى الورك تقريبًا.", "Reaches about the hips.") },
      { name: t("قصير (Crop)", "Crop"), text: t("ينتهي فوق الخصر؛ رائج في الأزياء النسائية.", "Ends above the waist; popular in womenswear.") },
      { name: t("طويل", "Longline"), text: t("أطول من العادي ويغطي أعلى الفخذ.", "Longer than regular, covering the top of the thighs.") },
    ],
  },
  sleeves: {
    title: t("أنواع الأكمام", "Sleeve styles"),
    intro: t("طريقة اتصال الكم بالجسم تغيّر شكل الأكتاف.", "How the sleeve joins the body changes the shoulder line."),
    items: [
      { name: t("عادية", "Regular"), text: t("الكم يُخاط عند نهاية الكتف؛ مظهر كلاسيكي.", "The sleeve is sewn at the end of the shoulder; a classic look.") },
      { name: t("كتف ساقط", "Drop shoulder"), text: t("خياطة الكتف أسفل من الكتف الطبيعي؛ مظهر واسع مريح يناسب الأوفر سايز.", "The shoulder seam sits below the natural shoulder; a relaxed look that suits oversized fits.") },
      { name: t("راجلان", "Raglan"), text: t("الكم يمتد قطريًا حتى الرقبة؛ رياضي ويسمح بحركة أكبر.", "The sleeve runs diagonally up to the neck; sporty, with more movement.") },
      { name: t("خفاشية", "Batwing"), text: t("كم واسع جدًا عند الإبط يضيق عند المعصم.", "Very wide at the armpit, narrowing at the wrist.") },
    ],
  },
  patterns: {
    title: t("أنواع النقشات", "Pattern types"),
    intro: t("شكل اللون أو الرسم على كامل القماش.", "The colour or print pattern across the whole fabric."),
    items: [
      { name: t("سادة", "Solid"), text: t("لون واحد؛ الأنسب لإبراز الشعار.", "One colour; the best background for a logo.") },
      { name: t("ألوان متداخلة", "Colour block"), text: t("أجزاء بألوان مختلفة.", "Panels in different colours.") },
      { name: t("طباعة كاملة", "All-over print"), text: t("تصميم يغطي القماش كله؛ يُطبع غالبًا قبل القص.", "A design across the whole fabric, usually printed before cutting.") },
      { name: t("تاي داي", "Tie-dye"), text: t("صبغ يدوي بتموجات ألوان؛ كل قطعة تختلف قليلًا.", "Hand dyeing with swirls of colour; every piece is a little different.") },
      { name: t("مموّه", "Camouflage"), text: t("نقشة التمويه العسكرية.", "The military camo pattern.") },
      { name: t("مخطط", "Striped"), text: t("خطوط أفقية أو عمودية في نسيج القماش أو مطبوعة.", "Horizontal or vertical stripes, knitted in or printed.") },
      { name: t("رسومات أو حروف", "Graphic or letters"), text: t("رسومات أو كتابات كجزء من التصميم.", "Graphics or lettering as part of the design.") },
    ],
  },
  styles: {
    title: t("الطابع العام", "Styles"),
    intro: t("كلمات تصف روح القطعة؛ تساعد المصنع على فهم ما تتخيله. يمكنك اختيار أكثر من واحد.", "Words for the overall feel; they help the factory understand what you have in mind. Pick as many as fit."),
    items: [
      { name: t("ستريت وير", "Streetwear"), text: t("قصّات واسعة وتصاميم جريئة مستوحاة من ثقافة الشارع.", "Loose cuts and bold designs from street culture.") },
      { name: t("كاجوال", "Casual"), text: t("مريح للاستخدام اليومي.", "Comfortable for everyday wear.") },
      { name: t("رياضي", "Sporty"), text: t("خامات وقصّات تناسب الحركة والرياضة.", "Fabrics and cuts for movement and sport.") },
      { name: t("بسيط", "Minimalist"), text: t("ألوان هادئة وتفاصيل قليلة.", "Calm colours and few details.") },
      { name: t("للجنسين", "Unisex"), text: t("قصّة تناسب الرجال والنساء.", "A cut that suits both men and women.") },
    ],
  },
  features: {
    title: t("مزايا القماش", "Fabric features"),
    intro: t("خصائص إضافية تطلبها من المصنع؛ بعضها يحتاج معالجة خاصة للقماش.", "Extra properties to ask the factory for; some need a special fabric finish."),
    items: [
      { name: t("يسمح بالتهوية", "Breathable"), text: t("يمرر الهواء والرطوبة فيبقى مريحًا.", "Lets air and moisture through so it stays comfortable.") },
      { name: t("دافئ", "Warm"), text: t("قماش أثقل أو مُمشّط من الداخل.", "A heavier or brushed fabric.") },
      { name: t("مقاوم للوبر", "Anti-pilling"), text: t("لا تتكون عليه كرات صغيرة بعد الغسيل والاحتكاك.", "Doesn't form little balls after washing and rubbing.") },
      { name: t("مقاوم للانكماش", "Anti-shrink"), text: t("قماش معالج مسبقًا ليحافظ على مقاسه بعد الغسيل.", "Pre-treated fabric that keeps its size after washing.") },
      { name: t("سريع الجفاف", "Quick-dry"), text: t("يجف بسرعة؛ شائع في البوليستر والملابس الرياضية.", "Dries fast; common in polyester and sportswear.") },
      { name: t("مقاوم للماء", "Water-resistant"), text: t("طبقة معالجة تصدّ الرذاذ الخفيف.", "A finish that repels light rain.") },
      { name: t("صديق للبيئة", "Eco-friendly"), text: t("خامات عضوية أو معاد تدويرها أو صبغات أقل ضررًا.", "Organic or recycled materials, or lower-impact dyes.") },
    ],
  },
  gender: {
    title: t("الفئة المستهدفة", "Who it's for"),
    intro: t("الفئة تحدد جدول المقاسات والقصّة التي يستخدمها المصنع.", "This decides which size chart and cut the factory uses."),
    items: [
      { name: t("للجنسين", "Unisex"), text: t("قصّة واحدة للجميع، غالبًا بمقاسات رجالية.", "One cut for everyone, usually on men's sizing.") },
      { name: t("رجالي", "Men"), text: t("أكتاف أعرض وطول أكبر.", "Broader shoulders and longer body.") },
      { name: t("نسائي", "Women"), text: t("قصّة أضيق عند الخصر وأكتاف أصغر.", "Narrower at the waist with smaller shoulders.") },
      { name: t("أطفال", "Kids"), text: t("مقاسات بالأعمار، وقد تحتاج شهادات سلامة إضافية.", "Sizes by age; may need extra safety certificates.") },
    ],
  },
  season: {
    title: t("الموسم", "Season"),
    intro: t("الموسم يساعد المصنع على اقتراح وزن القماش المناسب.", "The season helps the factory suggest the right fabric weight."),
    items: [
      { name: t("الشتاء", "Winter"), text: t("قماش أثقل (نحو 320–400 غرام/م²) ومُمشّط من الداخل.", "Heavier fabric (about 320–400 GSM), brushed inside.") },
      { name: t("الربيع والخريف", "Spring and autumn"), text: t("وزن متوسط (نحو 250–320 غرام/م²)، مثل الفرنش تيري.", "Medium weight (about 250–320 GSM), such as french terry.") },
      { name: t("الصيف", "Summer"), text: t("قماش خفيف يسمح بالتهوية.", "Light, breathable fabric.") },
      { name: t("كل المواسم", "All seasons"), text: t("وزن متوسط يناسب أغلب الأوقات.", "A medium weight for most of the year.") },
    ],
  },
  supply: {
    title: t("نوع التوريد", "Supply types"),
    intro: t("كيف يُصمَّم المنتج ومن يملك تصميمه.", "How the product is designed and whose design it is."),
    items: [
      { name: t("OEM — تصنيع بتصميمك", "OEM service"), text: t("يصنع المصنع تصميمك أنت بمواصفاتك وشعارك. الأنسب لبناء علامة خاصة.", "The factory makes your own design to your spec and logo. Best for building your own brand.") },
      { name: t("ODM — تصميم المصنع", "ODM service"), text: t("تختار تصميمًا جاهزًا من المصنع ويُعدَّل بإضافة علامتك. أسرع، والتصميم ليس حصريًا لك.", "You pick one of the factory's existing designs and add your brand. Faster, but the design isn't exclusive.") },
      { name: t("منتج جاهز مع شعارك", "Ready stock with your logo"), text: t("قطع مصنوعة مسبقًا يُضاف إليها شعارك. الأسرع وغالبًا بحد أدنى أقل للطلب.", "Pieces already made, with your logo added. The fastest, often with a lower minimum order.") },
    ],
  },
  colors: {
    title: t("اختيار الألوان", "Choosing colours"),
    intro: t("الألوان تظهر مختلفة على الشاشات، فالرمز الدقيق يضمن أن يطابق المصنع لونك.", "Colours look different on every screen, so an exact code makes sure the factory matches yours."),
    items: [
      { name: t("Pantone (TCX/TPX)", "Pantone (TCX/TPX)"), text: t("نظام الألوان الذي تستخدمه مصانع النسيج؛ الأدق لمطابقة لون القماش.", "The colour system textile factories use; the most accurate way to match fabric colour.") },
      { name: t("HEX", "HEX"), text: t("رمز لون الشاشة مثل ‎#FEB72F؛ مفيد كمرجع، والمصنع يقرّبه لأقرب صبغة.", "A screen colour code like #FEB72F; a useful reference that the factory matches to the closest dye.") },
      { name: t("ألوان علامتك", "Your brand colours"), text: t("احفظها في ملف النشاط لتظهر لك في كل طلب.", "Save them in your business profile to see them in every order.") },
    ],
  },
  artwork: {
    title: t("ملفات الشعار", "Logo files"),
    intro: t("جودة الملف تحدد جودة الطباعة أو التطريز.", "The quality of the file decides the quality of the print or embroidery."),
    items: [
      { name: t("ملفات متجهة (SVG، AI، EPS، PDF)", "Vector files (SVG, AI, EPS, PDF)"), text: t("الأفضل؛ تكبر وتصغر دون أن تفقد الوضوح.", "Best: they scale to any size without losing sharpness.") },
      { name: t("صور (PNG، JPG)", "Images (PNG, JPG)"), text: t("مقبولة إذا كانت بدقة عالية؛ PNG بخلفية شفافة أفضل.", "Fine if high resolution; PNG with a transparent background is better.") },
    ],
  },
  timeline: {
    title: t("مدة التنفيذ", "Timing"),
    intro: t("الوقت الكلي يشمل العينة والتصنيع والشحن.", "The total time covers the sample, production and shipping."),
    items: [
      { name: t("العينة", "Sample"), text: t("نحو أسبوع إلى أسبوعين.", "About one to two weeks.") },
      { name: t("التصنيع", "Production"), text: t("من أسبوعين إلى خمسة أسابيع بحسب الكمية والتفاصيل.", "Two to five weeks depending on quantity and details.") },
      { name: t("الشحن", "Shipping"), text: t("بالجو أسرع، وبالبحر أبطأ وأوفر للكميات الكبيرة.", "Air is faster; sea is slower and better value for large orders.") },
    ],
  },
  packaging: {
    title: t("التغليف", "Packaging"),
    intro: t("كيف تصل كل قطعة إليك وإلى زبونك.", "How each piece reaches you and your customer."),
    items: [
      { name: t("كيس بلاستيكي لكل قطعة", "Individual polybag"), text: t("الأساسي والأوفر، يحمي القطعة من الغبار.", "The basic, lowest-cost option; keeps dust off.") },
      { name: t("مطوية بورق مناديل", "Folded with tissue paper"), text: t("لمسة أنيقة عند فتح الطلب.", "An elegant touch when the order is opened.") },
      { name: t("على علّاقة", "On a hanger"), text: t("جاهزة للعرض في المحل.", "Ready to hang in a shop.") },
      { name: t("علبة تحمل شعارك", "Branded box"), text: t("تجربة فتح مميزة لعلامتك؛ عادةً الأعلى تكلفة.", "A memorable unboxing for your brand; usually the highest cost.") },
    ],
  },
  samples: {
    title: t("العينة", "Samples"),
    intro: t("قطعة واحدة تُصنع قبل الإنتاج الكامل لتتأكد من كل شيء.", "One piece made before full production so you can check everything."),
    items: [
      { name: t("نعم، عينة أولًا", "Yes, sample first"), text: t("تتأكد من الخامة والمقاس والشعار قبل دفع الكمية كلها. الأنسب لأول طلب.", "You check the fabric, size and logo before paying for the whole run. Best for a first order.") },
      { name: t("مباشرة للإنتاج", "Straight to production"), text: t("أسرع، لكن أي خطأ يظهر في الكمية كلها.", "Faster, but any mistake shows up in the whole run.") },
    ],
  },
  gsm: {
    title: t("وزن القماش (GSM)", "Fabric weight (GSM)"),
    intro: t("GSM هو وزن متر مربع من القماش بالغرام؛ كلما زاد الرقم كان القماش أسمك.", "GSM is the weight of one square metre of fabric in grams; the higher the number, the thicker the fabric."),
    items: [
      { name: t("160–200", "160–200"), text: t("تيشيرت خفيف.", "A light T-shirt.") },
      { name: t("200–240", "200–240"), text: t("تيشيرت ثقيل فاخر.", "A heavy, premium T-shirt.") },
      { name: t("280–320", "280–320"), text: t("هودي متوسط للربيع والخريف.", "A medium hoodie for spring and autumn.") },
      { name: t("320–400", "320–400"), text: t("هودي شتوي ثقيل.", "A heavy winter hoodie.") },
    ],
  },
  drawstrings: {
    title: t("حبال القلنسوة", "Hood drawstrings"),
    intro: t("الحبال تضبط فتحة القلنسوة وتضيف لمسة للتصميم.", "Drawstrings adjust the hood opening and add a design touch."),
    items: [
      { name: t("حبال قطنية مسطحة", "Flat cotton"), text: t("ناعمة وعصرية.", "Soft and modern.") },
      { name: t("حبل دائري", "Round cord"), text: t("كلاسيكي ومتين.", "Classic and sturdy.") },
      { name: t("بدون حبال", "No drawstrings"), text: t("مظهر أنظف، وأكثر أمانًا لملابس الأطفال.", "A cleaner look, and safer for children's wear.") },
    ],
  },
  pockets: {
    title: t("الجيوب", "Pockets"),
    intro: t("نوع الجيب يغيّر شكل الواجهة الأمامية.", "The pocket type changes the look of the front."),
    items: [
      { name: t("جيب كنغر", "Kangaroo pocket"), text: t("جيب واحد كبير في الأمام؛ الأشهر في الهوديز.", "One big pocket at the front; the most common on hoodies.") },
      { name: t("جيوب جانبية", "Side pockets"), text: t("جيبان منفصلان، شائعان مع السحّاب الكامل.", "Two separate pockets, common with full zips.") },
      { name: t("بدون جيب", "No pocket"), text: t("واجهة نظيفة تترك مساحة أكبر للطباعة.", "A clean front with more room for print.") },
    ],
  },
  sizing: {
    title: t("معايير المقاسات", "Size standards"),
    intro: t("المقاس نفسه يختلف بين الأنظمة، فاختيار المعيار يمنع المفاجآت.", "The same size differs between systems, so choosing the standard avoids surprises."),
    items: [
      { name: t("أمريكية/أوروبية", "US/EU sizing"), text: t("الأقرب لما اعتاده أغلب الزبائن في السعودية.", "Closest to what most customers in Saudi Arabia are used to.") },
      { name: t("آسيوية", "Asian sizing"), text: t("أصغر بمقاس تقريبًا؛ الافتراضي في المصانع الصينية.", "About one size smaller; the default in Chinese factories.") },
      { name: t("معيار المصنع", "Factory standard"), text: t("جدول المصنع الخاص، نتأكد منه معك قبل الإنتاج.", "The factory's own chart, which we confirm with you before production.") },
    ],
  },
  labels: {
    title: t("الملصقات", "Labels"),
    intro: t("الملصقات تعطي القطعة شكل منتج علامة حقيقية.", "Labels make the piece look like a real brand product."),
    items: [
      { name: t("ملصق رقبة منسوج", "Woven neck label"), text: t("ملصق قماشي بشعارك؛ الأفخم والأطول عمرًا.", "A fabric label with your logo; the most premium and longest lasting.") },
      { name: t("ملصق رقبة مطبوع", "Printed neck label"), text: t("مطبوع مباشرة على القماش؛ لا يحك الرقبة.", "Printed straight onto the fabric; never itchy.") },
      { name: t("ملصق المقاس والعناية", "Size and care labels"), text: t("تعليمات الغسيل والخامة والمقاس؛ قد تكون مطلوبة للبيع.", "Washing, material and size info; may be required for sale.") },
      { name: t("بطاقة معلّقة", "Hang tag"), text: t("بطاقة ورقية بعلامتك تُعلّق على القطعة.", "A paper tag with your brand attached to the piece.") },
    ],
  },
};

export const QUESTION_GUIDES: Record<string, string> = {
  material: "materials", fabric: "fabric_types", decoration_method: "printing",
  decoration_placement: "placement", hoodie_style: "hoodie_types",
  collar: "collars", neckline: "collars", fit_type: "fit", fit_reference: "fit", design: "design_details",
  length: "length", sleeve_style: "sleeves", pattern_type: "patterns", style: "styles", features: "features",
  gender: "gender", season: "season", supply_type: "supply", colors: "colors", artwork: "artwork",
  needed_by: "timeline", packaging: "packaging", sample: "samples", fabric_gsm: "gsm", drawstrings: "drawstrings",
  pocket: "pockets", size_standard: "sizing", labels: "labels",
};
