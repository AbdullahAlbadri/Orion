# Orion landing page — backgrounds, animation and interaction

Companion to `landing-redesign.md` (section numbers below match its structure). This file replaces the short "Motion" and "Pattern" rows in its visual-system table.

**Principle:** motion should explain, not decorate. Every animation either shows how Orion works, guides the eye to the next action, or confirms a click. Anything that does not do one of those is cut.

---

## 1. Timing rules (use everywhere)

| Token | Value | Used for |
|---|---|---|
| Micro | 150 ms | Hover colour, focus, button press |
| Standard | 250 to 300 ms | Accordions, modals, tabs, menus |
| Reveal | 500 to 600 ms | Scroll-in of sections and cards |
| Easing (default) | `cubic-bezier(0.22, 1, 0.36, 1)` (fast start, soft landing) | All of the above |
| Stagger | 80 ms between siblings | Cards, list items, steps |

- Animate only `transform` and `opacity` (smooth on phones). Never animate width, height or margins, except accordion height.
- Reveals play **once**, then stay.
- Nothing longer than 800 ms except the hero sequence and the journey path.

---

## 2. Navigation

- Transparent over the hero. After 40 px of scroll it becomes solid navy with a light blur behind it (200 ms).
- **Hide on scroll down, show on scroll up** (so it never covers content on a phone).
- A thin gold **scroll-progress bar** along its bottom edge.
- The current section's link gets a gold underline that slides between links (250 ms).
- Mobile menu: slides in from the side (RTL: from the right), links stagger in, page behind dims. Close on tap outside and on Escape.

---

## 3. Hero

### Background (layers, back to front)
1. Flat navy `#11101E`.
2. **Topographic lines** (SVG), gold-grey at 4 to 6 % opacity, drifting very slowly (60 s loop, a few pixels) and moving at 0.2× scroll speed (parallax).
3. **Soft gold glow** behind the mock-up: a blurred circle (about 600 px, 12 to 15 % opacity) that "breathes" between 100 % and 108 % scale over 8 s.
4. Optional film grain at 3 % to stop gradients from banding.
- Remove the red dashed line. If the team wants a path, use the journey line in section 11, which means something.

### Entrance
- Headline appears **word by word**: each word fades up 16 px, 60 ms apart, 600 ms each. Sub-line, buttons and the reassurance line follow with the standard stagger.
- Logo mark does a single gentle fade-in; it does not float or spin.

### The live mock-up (the main interaction)
A phone or browser frame with the chat on one side and the spec card on the other. It plays **once** on load, then rests:

| Time | What happens |
|---|---|
| 0.6 s | A customer message types out (about 40 ms per character): "أبغى أصنع هودي بشعار شركتي" |
| 2.0 s | Assistant "typing" dots for 600 ms, then the reply appears: "ممتاز! أي خامة تفضّل؟" |
| 3.0 s | Customer taps a quick-reply chip ("قطن 280 جم"); the chip lights gold |
| 3.4 s | Spec card rows appear one by one, 500 ms apart: الخامة, المقاس, الكمية, اللون. Each new row flashes a gold highlight for 400 ms |
| 6.0 s | A "ملخصك جاهز" tag slides in; everything rests |

- A small **replay** button (↻) restarts it. On hover or tap the spec card rows can be edited (shows that the customer stays in control).
- Label it **"مثال توضيحي"** so it is clearly an example, not a real order.
- Texts above are placeholders; final wording is the team's.

### Interaction
- Primary button: hover lifts 2 px with a soft gold glow; the arrow nudges 4 px in the reading direction (left in Arabic); press scales to 0.98.
- Secondary button: border fills with a subtle gold tint on hover.

---

## 4. Product strip

- A slim band with product names or small photos moving at a constant slow speed (about 40 px per second, direction follows RTL).
- **Pauses on hover and on focus**; stops completely with reduced motion.
- Fades out at both edges (gradient mask).

---

## 5. Why Orion (off-white section)

- Background: flat off-white. A very large **outlined "01"** sits behind the heading at 6 % opacity and drifts at 0.15× scroll speed.
- The image slides in from the side with a slight mask reveal (600 ms) and moves 5 % slower than the text (parallax).
- The four numbered points reveal one by one (stagger 80 ms). Each number counts as a small gold dot that fills when the point enters view.
- Hover on a point: the number turns gold and the point moves 4 px.

---

## 6. How it works (navy section): the scroll-driven timeline

This is the second signature interaction.

- **Desktop:** a two-column layout. One side holds the four steps as text, the other a **sticky device frame** that stays in place. As the visitor scrolls past each step, the screen inside the frame cross-fades to the matching real screenshot (chat and spec card → pre-receipt → quote → order timeline). 300 ms cross-fade with a slight vertical slide.
- A **vertical gold progress line** along the steps fills as the visitor scrolls. The active step is full brightness; others at 50 %.
- **Click or tap a step** to jump to its screen (also works with the keyboard).
- **Mobile:** steps stack; each has its own screenshot underneath, revealed on scroll. No sticky frame.
- No counters or day numbers.

---

## 7. Markets

- **Cards at rest:** photo, name, three example products.
- **Hover (desktop):** the photo zooms to 1.05 over 400 ms, a gold line draws along the bottom edge, and an arrow slides in. The card lifts 4 px.
- **Click:** opens a panel for the market (modal on desktop, bottom sheet on mobile) with a 250 ms scale and fade; the page behind dims. The panel lists the options, what the customer will be asked, and "ابدأ طلبًا في هذا المجال".
- **Waitlist cards:** the "أخبرني عند الإطلاق" button turns into an inline email field (250 ms), then a check mark and "شكرًا، سنخبرك" on success. `[TBD: waitlist backend]`
- The "متاح الآن" badge has a tiny pulsing dot (2 s loop, subtle).
- Mobile: swipeable row with snap points, or a stacked list.

---

## 8. Costs (navy section)

- Background: navy with a faint gold glow behind the receipt card.
- The three cost cards reveal with the standard stagger.
- **The illustrative quote card** builds itself when it enters view: rows appear one by one (product, fee, shipping), then a line draws, then the total row appears with a gold highlight. About 1.2 s in total, once.
- The three check marks **draw their stroke** (SVG, 300 ms each) one after the other.

---

## 9. People and trust (off-white)

- Portraits fade up with the stagger. On hover: a slight lift and a gold ring around the portrait.
- The three commitments reveal next to them; each icon draws its outline once.
- No auto-rotating carousels.

---

## 10. FAQ (navy)

- Tabs: a gold underline **slides** to the active tab (250 ms); content cross-fades.
- Accordion: height animates over 250 to 300 ms; the plus icon rotates 45° into a cross; only the first answer is open on load.
- Keyboard: arrow keys move between questions; Enter and Space toggle.
- Deep links: `/#faq-shipping` opens that question and scrolls to it.

---

## 11. The journey line (optional, replaces the red dashed line)

A thin **gold dashed path** that starts at the hero and winds down the page, linking the sections: idea → factory → your address. It **draws as the visitor scrolls** (stroke offset linked to scroll), and a small gold dot travels along its tip. Each section heading has a node the line passes through.
- It reinforces "the network between your idea and your factory", which is the page's promise.
- Desktop only. Hidden on mobile and with reduced motion.
- If it distracts during testing, remove it first.

---

## 12. Contact and closing band

- Contact: the WhatsApp button does **one** soft pulse when it first appears, then stays still. Form fields have a gold focus ring and a floating label (150 ms). On submit: button shows a loader, then a check and a confirmation message.
- Closing band (gold): the large line reveals **line by line** with a mask (each line slides up from behind a clipping edge, 500 ms, 120 ms stagger). The primary button on it is navy with gold text; hover brightens it and a light sheen passes once across.
- Footer: link underlines slide in on hover. Language toggle cross-fades the text (200 ms) and keeps the scroll position.

---

## 13. Mobile specifics

- Sticky bottom bar with "ابدأ طلبك" appears after the hero leaves the screen (slides up, 250 ms) and hides near the closing band so it doesn't duplicate it.
- Replace hover effects with press feedback (scale 0.98, 100 ms).
- Parallax and the journey line are off. The hero mock-up still plays but with fewer steps.
- Respect safe areas (notch, home indicator).

---

## 14. Accessibility and performance

- **`prefers-reduced-motion`:** turn off parallax, drifting backgrounds, the marquee, typing, path drawing and the pulse. Show final states immediately. Keep simple fades only.
- Any moving content that lasts over 5 seconds can be paused (marquee, replay).
- Animations pause when off-screen. Do not start the hero sequence if the tab is hidden.
- Keep layout from shifting: reserve space for images and the mock-up.
- No sound and no autoplay audio.
- Target: smooth 60 fps on a mid-range phone, and no animation blocking the first meaningful paint `[TBD: set Lighthouse targets]`.

## 15. Suggested tooling

The screenshot of the current page shows what looks like the Next.js dev badge, so it is probably Next.js. If so:
- **Motion (Framer Motion)** for reveals, the accordion, modals and the sticky-step screen switching.
- **CSS** for hover states, the strip, glows and the progress bar.
- CSS **scroll-driven animations** for the journey line and timeline where supported, with an IntersectionObserver fallback.
- Avoid heavy 3D, video backgrounds and large Lottie files. If a hero video is wanted later, keep it under about 2 MB, muted, and never required to understand the page.

## 16. Acceptance check

- The hero mock-up shows what Orion does within 6 seconds, with nothing needed from the visitor.
- Every animation has a purpose (explain, guide, confirm).
- No animation hides or delays content a visitor needs to read.
- With reduced motion on, the page is complete and readable.
- The page stays smooth when scrolled quickly on a phone.

## 17. Decisions needed

1. Keep the journey line, or skip it?
2. Hero mock-up: should the chat text be in Arabic only, or switch with the language?
3. Real screenshots of the app screens for the timeline: will they exist before launch, or use clean mock-ups?
4. Waitlist: build it, or hide the five other markets for now?
