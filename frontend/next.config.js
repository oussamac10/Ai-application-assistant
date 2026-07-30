/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    // The rewrite below proxies /api/* to the backend. Next's proxy gives up
    // after 30s by default and answers the browser with a bare
    // "Internal Server Error" (HTTP 500, not JSON) while the backend is still
    // working — which is exactly how a slow prepare-questions request
    // surfaced to users as a processing failure on a document that in fact
    // succeeded. Question preparation runs Azure/OCR plus AI translation
    // synchronously, so it needs a ceiling above that. Moving preparation to
    // a background job is Phase 17; until then this is the honest bound.
    proxyTimeout: 180_000,
  },
  async rewrites() {
    const backendUrl = process.env.BACKEND_API_URL || "http://localhost:8000";
    return [
      {
        source: "/api/:path*",
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;
