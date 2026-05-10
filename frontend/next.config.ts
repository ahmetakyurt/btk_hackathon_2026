import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  typescript: {
    // NextAuth v5 beta has type augmentation issues with 'next-auth/jwt'.
    // Types are verified locally; skip in production build.
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
