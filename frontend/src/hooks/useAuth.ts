import { useMemo } from 'react';
import { getToken, getUserId } from '@/api/client';

interface AuthState {
  user: {
    username: string;
    role: string;
  } | null;
  isAuthenticated: boolean;
  token: string | null;
}

export function useAuth(): AuthState {
  return useMemo(() => {
    const token = getToken();
    const username = getUserId();
    const role = localStorage.getItem('user_role') || 'user';

    if (!token) {
      return {
        user: null,
        isAuthenticated: false,
        token: null,
      };
    }

    return {
      user: {
        username,
        role,
      },
      isAuthenticated: true,
      token,
    };
  }, []);
}
