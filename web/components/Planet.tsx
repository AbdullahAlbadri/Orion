// A product drawn as a planet: a flat round body with the product type drawn inside in gold lines, and a tilted
// ring whose back half passes behind the planet and front half across it. Used on the Overview ("Order again")
// and on My Products. The ring tilts a little when its card is hovered (see .planet in app.css).
import { ProductThumb } from "./ui";

export default function Planet({ option, size = 92 }: { option: string | null; size?: number }) {
  return (
    <span className="planet" style={{ ["--size" as string]: `${size}px` }} aria-hidden>
      <span className="planet-ring" />
      <span className="planet-orb"><ProductThumb option={option} size={Math.round(size * 0.7)} /></span>
      <span className="planet-ring front" />
    </span>
  );
}
