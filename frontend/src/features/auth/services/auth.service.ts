import {
  signIn,
  signUp,
  signOut,
  fetchAuthSession,
  getCurrentUser,
} from 'aws-amplify/auth';
import { AuthUser } from '@/types';

export async function register(email: string, password: string): Promise<void> {
  await signUp({
    username: email,
    password,
    options: { userAttributes: { email } },
  });
}

export async function login(email: string, password: string): Promise<AuthUser> {
  await signIn({ username: email, password });
  return getCurrentAuthUser();
}

export async function logout(): Promise<void> {
  await signOut();
}

export async function getCurrentAuthUser(): Promise<AuthUser> {
  const { userId } = await getCurrentUser();
  const session = await fetchAuthSession();
  const idToken = session.tokens?.idToken;
  const payload = idToken?.payload ?? {};

  return {
    sub: userId,
    email: (payload['email'] as string) ?? '',
    idToken: idToken?.toString() ?? '',
  };
}
