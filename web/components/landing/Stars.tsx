// Hero sky: a quiet starfield. The stars come from a fixed seed so the server and the browser draw the same sky.
// Twinkling stops for reduced motion.
const STARS = (() => {
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const round = (n: number) => Math.round(n * 10) / 10;
  return Array.from({ length: 90 }, () => ({
    x: round(rnd() * 1440), y: round(rnd() * 900), r: round(0.4 + rnd() * 1.1), twinkle: rnd() < 0.35, delay: round(rnd() * 6),
  }));
})();

export default function Stars() {
  return (
    <svg className="ln-stars" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden>
      {STARS.map((s, i) => (
        <circle key={i} cx={s.x} cy={s.y} r={s.r} className={s.twinkle ? "tw" : undefined}
          style={s.twinkle ? { ["--d" as string]: `${s.delay}s` } : undefined} />
      ))}
    </svg>
  );
}
