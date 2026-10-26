// Behind the signed-in pages: a night sky. Faint stars (some twinkle), one wide tilted orbit with a light
// going slowly round, a warm glow in a corner and light film grain, all fixed while the page scrolls.
// The stars come from a fixed seed so the server and the browser draw the same sky. Still for reduced motion.
const STARS = (() => {
  let seed = 11;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const round = (n: number) => Math.round(n * 10) / 10;
  return Array.from({ length: 110 }, () => ({
    x: round(rnd() * 1600), y: round(rnd() * 1000), r: round(0.35 + rnd() * 1), twinkle: rnd() < 0.3, delay: round(rnd() * 7),
  }));
})();

export default function Sky() {
  return (
    <div className="sky" aria-hidden>
      <svg viewBox="0 0 1600 1000" preserveAspectRatio="xMidYMid slice">
        {STARS.map((s, i) => (
          <circle key={i} className={s.twinkle ? "sky-star tw" : "sky-star"} cx={s.x} cy={s.y} r={s.r}
            style={s.twinkle ? { ["--d" as string]: `${s.delay}s` } : undefined} />
        ))}
        <g transform="rotate(-14 800 560)">
          <ellipse className="sky-orbit" cx="800" cy="560" rx="760" ry="230" />
          <ellipse className="sky-orbit faint" cx="800" cy="560" rx="560" ry="150" />
          <path id="sky-orbit-path" fill="none" d="M40 560 A760 230 0 1 1 1560 560 A760 230 0 1 1 40 560" />
          <circle className="sky-light" r="3">
            <animateMotion dur="60s" repeatCount="indefinite"><mpath href="#sky-orbit-path" /></animateMotion>
          </circle>
        </g>
      </svg>
    </div>
  );
}
