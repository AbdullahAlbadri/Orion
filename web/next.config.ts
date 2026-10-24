import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // A separate build folder lets a second copy run beside `npm run dev` (used for screenshots)
  distDir: process.env.NEXT_DIST_DIR || ".next",
  output: "standalone", // small Docker image for deployment (step 7)
  poweredByHeader: false,
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
