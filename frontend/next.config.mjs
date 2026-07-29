/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Required for aws-amplify SSR compatibility
  transpilePackages: ['@aws-amplify/ui-react', 'aws-amplify'],
};

export default nextConfig;
