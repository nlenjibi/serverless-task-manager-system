import { Amplify } from 'aws-amplify';
import { AWS_CONFIG } from './constants';

export function configureAmplify() {
  Amplify.configure({
    Auth: {
      Cognito: {
        userPoolId: AWS_CONFIG.userPoolId,
        userPoolClientId: AWS_CONFIG.userPoolClientId,
        loginWith: { email: true },
      },
    },
  });
}
