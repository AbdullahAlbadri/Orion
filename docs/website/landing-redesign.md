# Orion landing page — redesign brief

Replaces `01-home.md`. Route `/`. Arabic first (RTL), English second, mobile first.
Inspiration: sybiosme.com/en (structure and rhythm, not its look). Brand: gold `#FEB72F`, red `#BC3039`, navy `#11101E`, off-white `#F8F8F8`; Work Sans (Latin), Cairo (Arabic stand-in for Swissra).

Anything marked `[TBD]` needs a team decision. No invented prices, statistics, testimonials, timelines or photos.

---

## 1. Remove customs clearance everywhere

Orion does **not** offer customs clearance (تخليص جمركي). Delete every mention from the landing page:

| Where (current page) | Current text | Action |
|---|---|---|
| Hero sub-line | "...والشحن والأوراق الجمركية" | Remove the customs part (new copy below) |
| "Why is manufacturing hard" cards | "الشحن والجمارك: منتج جيد قد يتعطل عند الشحن أو الأوراق الجمركية" | Delete the card. Replace with a shipping-free point (see section 4) |
| "What does it cost" cards | "الجمارك والرسوم: رسوم الاستيراد عند الوصول" | Delete the card |
| FAQ | "من يتولى الجمارك؟" | Delete the question |
| Anywhere else | "customs", "duties", "paperwork" | Search and remove |

**One thing I'd keep, as a single honest line:** a FAQ item "هل تتولون التخليص الجمركي؟ — لا. نشحن البضاعة إلى عنوانك، والتخليص يتم عبر `[TBD: شركة الشحن / أنت]`." Without it, customers may assume clearance is included and be surprised by charges. Delete it if you disagree, but then say nothing on the page that implies it is covered.

Decision for the team: the earlier product design had a paperwork system that fills customs forms. If that is gone too, tell me and I'll update the app pages (see section 12).

---

## 2. What is wrong with the current page

From the screenshot:
- **Everything looks the same.** Every section is a row of small dark bordered cards, so nothing leads the eye and the page reads as one long grey strip.
- **No product, no people, no proof.** The hero is a floating logo and text. A visitor sees no example of what Orion actually does.
- **Low contrast, tiny text.** Grey body text on near-black is hard to read, especially in Arabic.
- **Narrow column on a wide screen.** The content sits in a thin centre strip with large empty sides.
- **Decoration without meaning.** The topographic pattern, the red dashed line and the "+" corner marks add noise. The "+" in the cost cards looks like a button.
- **Repeated icons.** The three trust cards use the same shield icon, so none stands out.
- **FAQ is a list of closed rows.** Nothing is visible without clicking.
- **Markets look disabled.** "قريبًا" badges on five of six markets make the product feel unfinished.

## 3. What to borrow from Sybiosme

- A large, confident headline with one clear promise and two buttons (primary and secondary).
- Numbered sections (01, 02, 03) so the page feels organised.
- A simple timeline for the process.
- A visual "work" gallery that proves what the company makes.
- Short, direct sentences, and reassurance next to the call to action ("no commitment").
- Real people (team portraits) near the contact section.
- FAQ grouped by topic, with the first answer already open.
- A closing band with a final call to action.

What **not** to copy: subscriptions, a checkout on the landing page, or a "refund if late" promise. Orion works per order.

---

## 4. Page structure

Alternate **navy** and **off-white** sections for rhythm. One idea per section, one main visual per section.

### 0. Navigation (sticky)
Logo · How it works · Markets · Costs · FAQ · Contact · language toggle · Sign in · **Start your order** (primary button).
Transparent over the hero, solid navy after scrolling. On mobile: logo, language, menu; the order button stays visible.

### 1. Hero (navy)
- **Headline:** الشبكة الوحيدة بين فكرتك ومصنعك
  EN: The only network between your idea and your factory.
- **Sub-line (AR):** صف منتجك للمساعد الذكي، وراجع ملخصًا واضحًا، ونتولى التواصل مع المصنع والشحن إلى عنوانك.
  **(EN):** Describe your product to our AI assistant, review a clear summary, and we handle the factory and shipping to your address.
- **Buttons:** ابدأ طلبك / Start your order (primary) · كيف نعمل / How it works (secondary, scrolls).
- **Reassurance line under the buttons:** لا تدفع شيئًا قبل أن توافق على عرض السعر `[TBD: confirm this is true]`.
- **Visual (replaces the floating logo):** a product mock-up. On one side a short Arabic chat with the assistant, on the other a **spec card filling in live** ("الخامة: قطن 280 جم · المقاس: L · الكمية: 200"). It shows the product working in two seconds. Animate it gently (typing, fields appearing), and respect "reduce motion".
- Background: plain navy with a very faint topographic pattern (about 4% opacity) in the hero only.

### 2. Product strip
A slim band under the hero with product names or photos scrolling slowly: هودي · عباية · دفتر تخطيط · غطاء وسادة · قلادة حيوانات · كيس شحن. Acts like Sybiosme's repeated wordmark divider.

### 3. Why Orion (off-white) — "01"
- **Heading:** شبكة مصانع تعمل لصالحك
  EN: A factory network that works for you.
- Left or right: one large image (a workshop or sample photo `[TBD: real photo]`). Opposite side: four numbered points.
  1. **جهة اتصال واحدة** — بدل مراسلة عشرات المصانع، تتحدث معنا فقط.
  2. **لا شيء ينقص** — المساعد يسأل ما يسأله المصنع، ويقارن كل رد بطلبك.
  3. **كل خطوة مرئية** — ملخص قبل الطلب، وعرض سعر واضح، وصور وتحديثات، وتتبع للشحنة.
  4. **منتجاتك محفوظة** — أعد الطلب بضغطة دون إعادة الأسئلة.
- This replaces the three problem cards. No shipping/customs point.

### 4. How it works (navy) — "02"
- **Heading:** من فكرتك إلى مستودعك في أربع خطوات
  EN: From your idea to your warehouse in four steps.
- A horizontal timeline on desktop, vertical on mobile, with a line that fills as the visitor scrolls. Each step has a small screenshot of the real screen:
  1. **صف فكرتك** — المساعد يسألك عن التفاصيل ويقبل صورك وملفاتك. *(screen: chat and spec card)*
  2. **راجع ملخصك** — ترى منتجك كاملًا قبل أن يُرسل لأي مصنع. *(screen: pre-receipt)*
  3. **وافق على العرض والعينة** — يصلك عرض السعر، وتقرر متى تكمل. *(screen: quote)*
  4. **تابع كل شيء** — إنتاج وشحن وتحديثات بالصور في مكان واحد. *(screen: order timeline)*
- Do **not** add day counts or "in 10 days" style claims until real timings exist `[TBD]`.

### 5. Markets (off-white) — "03"
- **Heading:** ماذا نصنع لك؟ / What can we make for you?
- Six **large image cards** (3×2 desktop, 1 column mobile): photo, market name, three example products, status.
  - Available now: الأزياء والملابس والزي الموحد (clear "متاح الآن" badge, primary button "ابدأ طلبًا في هذا المجال").
  - The other five: don't show a disabled-looking "قريبًا" badge. Use a visible but calm label "يفتح قريبًا" and a button **"أخبرني عند الإطلاق"** (waitlist), so each card still does something `[TBD: waitlist or hide until launch]`.
- Cards open the same panel as now (products, what you'll be asked), but as a proper modal or page section, not a tiny expanding box.
- Do not describe any market as free of regulations.

### 6. Costs (navy) — "04"
- **Heading:** مم تتكون التكلفة؟ / What does it cost?
- Three cards only, large and plain, without "+" marks:
  1. **تكلفة المنتج** — سعر المصنع لمنتجك وكميتك.
  2. **رسوم أوريون** — رسوم خدمتنا، واضحة في عرض السعر `[TBD: fee model]`.
  3. **الشحن** — من المصنع إلى عنوانك `[TBD: method and who books it]`.
- **Illustrative quote layout:** a clean receipt card showing the structure (product, fee, shipping, total) with labelled rows and **no numbers** (or numbers only if real). Caption: "هكذا يظهر عرض السعر قبل أن تؤكد".
- Three check-mark lines:
  - ترى كل التكاليف قبل أن تؤكد.
  - الأسعار تأتي من المصانع، وفريقنا هو من يتولى الاتفاق عليها. الذكاء الاصطناعي لا يتفاوض على الأسعار.
  - لا أسعار تقديرية.
- Remove the customs card and any "fees at arrival" wording.

### 7. People and trust (off-white) — "05"
- **Heading:** وراء أوريون فريق حقيقي / A real team behind Orion.
- Three portraits with name and role: معاذ العمودي (قائد الفريق) · عبدالله البدري (مهندس ذكاء اصطناعي) · سامر الغامدي (المدير المالي) `[TBD: photos and each person's consent]`.
- Three plain commitments next to them, each with a different small icon:
  - ملفاتك خاصة: شعارك وصورك لا يراها إلا أنت وفريقنا `[TBD: confirm this is accurate]`.
  - كل شيء قبل التأكيد: مواصفات كاملة ثم تكاليف كاملة قبل أي التزام.
  - فريق بشري خلف الذكاء الاصطناعي: أي سؤال عن السعر أو التغيير يراجعه فريقنا.
- Company details (registered name, address) `[TBD]`.

### 8. FAQ (navy) — "06"
- **Heading:** أسئلتك، وأجوبتنا / Your questions, our answers.
- Tabs by topic. **The first answer is open by default.**
  - **الطلب:** ما هو أوريون؟ · هل يمكنني رفع صور وملفات؟ · ما هو الملخص قبل الطلب؟ · كيف أتابع طلبي؟
  - **التكلفة والدفع:** مم تتكون التكلفة؟ · هل أرى كل التكاليف قبل التأكيد؟ · هل يتفاوض الذكاء الاصطناعي على السعر؟ (لا) · كيف أدفع؟ `[TBD]`
  - **العينات:** هل يمكنني طلب عينة؟ `[TBD: sample policy, answer only when decided]`
  - **الشحن:** من يتولى الشحن؟ نشحن إلى عنوانك `[TBD]` · هل تتولون التخليص الجمركي؟ لا، انظر القسم 1.
  - **الخصوصية:** هل بياناتي آمنة؟ (رابط الخصوصية)
- Leave out any question the team has not decided; don't write vague answers.

### 9. Contact (off-white) — "07"
- **Heading:** عندك سؤال؟ نتحدث / Another question? Let's talk.
- Primary button: **واتساب** `[TBD: number]`, secondary: email. Short form: name, email, message.
- Support hours in Riyadh time `[TBD]`.

### 10. Closing band (gold)
- Big statement: هذه نهاية الصفحة. بداية منتجك من هنا. / This is the end of the page. Your product starts here.
- Two buttons: ابدأ طلبك · تحدث إلينا.
- Navy text on gold for contrast.

### 11. Footer (navy)
Logo, section links, "الشروط والخصوصية" (opens the legal drawer), language toggle, social links `[TBD]`, © أوريون, city `[TBD]`.

---

## 5. Visual system

| Topic | Rule |
|---|---|
| **Backgrounds** | Alternate navy `#11101E` and off-white `#F8F8F8`. No full-page dark wall. |
| **Primary button** | Gold `#FEB72F` fill, navy text. Keep **red** `#BC3039` for errors and warnings only, so the call to action is the one gold thing on screen. If the team prefers the current red button, keep it, but use one primary colour everywhere. |
| **Headings** | Cairo bold. Hero 56 to 72 px on desktop, 36 to 40 on mobile. Section headings 36 to 44 px. Short lines, one idea each. |
| **Body text** | 18 px desktop, 16 mobile, line height about 1.7. On navy use light text (about `#D9D9E0`), never mid-grey. Aim for contrast 4.5:1 or better. |
| **Layout** | Container up to 1200 px, generous side margins, 96 px section padding on desktop (56 on mobile). |
| **Cards** | Fewer and larger. Rounded corners (16 to 20 px), real images, one clear action each. Remove the "+" corner marks. |
| **Imagery** | Real product and factory photos, team portraits, screenshots of the real app. Stock images only if clearly generic. No fake testimonials or logos. |
| **Pattern** | Topographic lines only in the hero, very faint. Remove the red dashed line. |
| **Icons** | One line-icon style, different icon per idea, gold on navy. |
| **Motion** | Subtle: fade-up on scroll, timeline line filling, hero mock-up typing. Honour `prefers-reduced-motion`. No auto-playing sound. |
| **Numbering** | Section labels 01 to 07 in small gold text above each heading. |

## 6. RTL and mobile

- Build RTL first. Mirror arrows and the timeline direction. Keep digits and Latin product names (Work Sans) aligned correctly inside Arabic text.
- Mobile: single column, hero mock-up below the buttons, **sticky bottom bar** with "ابدأ طلبك", timeline vertical, markets as a horizontally swipeable row or a stacked list.
- Tap targets at least 44 px.

## 7. Technical notes

- Images in WebP/AVIF, lazy-loaded, with sizes. Fonts subset, `font-display: swap`.
- Language switch keeps the visitor on the same section.
- Meta: Arabic title and description, Open Graph image, `lang` and `dir` set per language.
- Analytics and cookie banner only if needed `[TBD]`.
- Accessibility: skip link, visible focus, alt text, keyboard-friendly FAQ and modals.

## 8. Assets to prepare

- Real product photos for the six markets (at least apparel now)
- Screenshots of the real chat/spec card, pre-receipt, quote and order timeline (or clean mock-ups)
- Team portraits and consent
- Logo mark in gold, navy and white (already extracted per the brand reference)
- WhatsApp number, support email, company details

## 9. Decisions needed

1. Customs: should the paperwork system stay (documents for shipment) or go entirely?
2. Waitlist for the five markets that are not open yet, or hide them for now?
3. Primary button colour: gold (recommended) or keep red?
4. Reassurance line ("pay nothing before you approve the quote"): confirm it is true.
5. Fee model and shipping method wording for the costs section.
6. Photos and team consent.

## 10. Build order

1. Hero with the live mock-up, navigation and the closing band
2. Why Orion, How it works, Markets
3. Costs, People, FAQ, Contact, Footer
4. Mobile pass, RTL check, accessibility and speed check
5. Replace placeholders with real photos and copy

## 11. Acceptance check

- A new visitor can say in 10 seconds what Orion does.
- The page has **no** mention of customs clearance, duties at arrival, or customs paperwork (except the optional honest FAQ line).
- Every section has one clear focus and one visual that is not just a card.
- Text is readable on a phone in sunlight.
- Every claim on the page is something the team can prove.

## 12. Other files that mention customs (not yet changed)

These still mention customs and should be updated once you answer decision 1: `01-home.md` (replaced by this file), `00-sitemap.md`, `02-start.md` (customs fields in onboarding), and in `app/`: `10-overview`, `12-new-order`, `13-order-page`, `14-shipments`, `16-stats`, `18-documents`, `20-business-profile`, `22-settings`, `23-later`.
