// Thmanyah typeface (thmanyah.com), Arabic and Latin. The licence forbids uploading the font files anywhere,
// GitHub included: they live in web/fonts/ (git-ignored) and each machine downloads them from thmanyah.com.
// TODO(decide): Thmanyah's written confirmation that web embedding like this is allowed (asked by email).
// next/font needs the paths written out in full.
import localFont from "next/font/local";

export const thSans = localFont({
  src: [
    { path: "../fonts/Thmanyah-Font-Family/thmanyah typeface/thmanyahsans/woff2/thmanyahsans-Light.woff2", weight: "300" },
    { path: "../fonts/Thmanyah-Font-Family/thmanyah typeface/thmanyahsans/woff2/thmanyahsans-Regular.woff2", weight: "400" },
    { path: "../fonts/Thmanyah-Font-Family/thmanyah typeface/thmanyahsans/woff2/thmanyahsans-Medium.woff2", weight: "500" },
    { path: "../fonts/Thmanyah-Font-Family/thmanyah typeface/thmanyahsans/woff2/thmanyahsans-Bold.woff2", weight: "700" },
  ],
  variable: "--font-th-sans",
  display: "swap",
});

export const thDisplay = localFont({
  src: [
    { path: "../fonts/Thmanyah-Font-Family/thmanyah typeface/thmanyahserifdisplay/woff2/thmanyahserifdisplay-Regular.woff2", weight: "400" },
    { path: "../fonts/Thmanyah-Font-Family/thmanyah typeface/thmanyahserifdisplay/woff2/thmanyahserifdisplay-Medium.woff2", weight: "500" },
    { path: "../fonts/Thmanyah-Font-Family/thmanyah typeface/thmanyahserifdisplay/woff2/thmanyahserifdisplay-Bold.woff2", weight: "700" },
  ],
  variable: "--font-th-display",
  display: "swap",
});
