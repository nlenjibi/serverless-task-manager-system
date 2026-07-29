// Populated at build time by Amplify environment variables.
// Set these in the Amplify Console → App settings → Environment variables.
export const AWS_CONFIG = {
  region: process.env.NEXT_PUBLIC_AWS_REGION ?? '',
  userPoolId: process.env.NEXT_PUBLIC_USER_POOL_ID ?? '',
  userPoolClientId: process.env.NEXT_PUBLIC_USER_POOL_CLIENT_ID ?? '',
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? '',
} as const;
