// Hero sky: a quiet starfield and the Orion constellation the name comes from. The stars come from a fixed seed
// so the server and the browser draw the same sky. Twinkling and line drawing stop for reduced motion.
const STARS = (() => {
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const round = (n: number) => Math.round(n * 10) / 10;
  return Array.from({ length: 90 }, () => ({
    x: round(rnd() * 1440), y: round(rnd() * 900), r: round(0.4 + rnd() * 1.1), twinkle: rnd() < 0.35, delay: round(rnd() * 6),
  }));
})();

// Orion as seen from Saudi Arabia: Meissa (head), Betelgeuse and Bellatrix (shoulders), the belt, Saiph and Rigel
const ORION: Record<string, [number, number, number]> = {
  meissa: [100, 22, 2.2], betelgeuse: [42, 58, 4.2], bellatrix: [168, 72, 3], mintaka: [128, 160, 2.6],
  alnilam: [104, 170, 3], alnitak: [80, 182, 2.8], saiph: [58, 282, 2.8], rigel: [180, 270, 4],
};
const LINES = [["meissa", "betelgeuse"], ["meissa", "bellatrix"], ["betelgeuse", "alnitak"], ["bellatrix", "mintaka"],
  ["alnitak", "alnilam"], ["alnilam", "mintaka"], ["alnitak", "saiph"], ["mintaka", "rigel"]];

export default function Stars() {
  return (
    <>
      <svg className="ln-stars" viewBox="0 0 1440 900" preserveAspectRatio="xMidYMid slice" aria-hidden>
        {STARS.map((s, i) => (
          <circle key={i} cx={s.x} cy={s.y} r={s.r} className={s.twinkle ? "tw" : undefined}
            style={s.twinkle ? { ["--d" as string]: `${s.delay}s` } : undefined} />
        ))}
      </svg>
      <div className="ln-constellation" aria-hidden>
        <svg viewBox="0 0 220 300">
          {LINES.map(([a, b], i) => (
            <line key={i} className="ln-const-line" pathLength={1} style={{ ["--i" as string]: i }}
              x1={ORION[a][0]} y1={ORION[a][1]} x2={ORION[b][0]} y2={ORION[b][1]} />
          ))}
          {Object.entries(ORION).map(([name, [x, y, r]], i) => (
            <circle key={name} className={`ln-const-star ${name}`} cx={x} cy={y} r={r} style={{ ["--d" as string]: `${i * 0.7}s` }} />
          ))}
        </svg>
        <span dir="ltr">ORION</span>
      </div>
    </>
  );
}
