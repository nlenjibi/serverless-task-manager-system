import axios from 'axios';
import { fetchAuthSession } from 'aws-amplify/auth';
import { AWS_CONFIG } from './constants';

const http = axios.create({ baseURL: AWS_CONFIG.apiUrl });

// Attach the Cognito ID token to every request
http.interceptors.request.use(async (config) => {
  const session = await fetchAuthSession();
  const token = session.tokens?.idToken?.toString();
  if (token) config.headers.Authorization = token;
  return config;
});

export default http;
