/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  reactStrictMode: true,
  // The browser calls /api/...; Next.js forwards to the backend, so the session cookie is same-origin.
  // Baked in at build time: Docker passes VIGIL_API_URL=http://backend:8000.
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.VIGIL_API_URL ?? "http://localhost:8000"}/:path*` }];
  },
};
export default nextConfig;
