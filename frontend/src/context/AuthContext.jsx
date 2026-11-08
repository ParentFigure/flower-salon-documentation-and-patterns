import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { getCurrentUser, loginUser, registerClient } from "../api/auth";
import { getAccessToken, setAccessToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(getAccessToken()));

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return null;
    }

    setLoading(true);
    try {
      const currentUser = await getCurrentUser();
      const normalizedUser = {
        ...currentUser,
        role: String(currentUser.role || "").toUpperCase(),
      };
      setUser(normalizedUser);
      return normalizedUser;
    } catch {
      setAccessToken(null);
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email, password) => {
    const result = await loginUser(email, password);
    setAccessToken(result.access_token);
    const currentUser = await refreshUser();

    if (!currentUser) {
      throw new Error("Сесію не вдалося підтвердити. Спробуйте увійти ще раз.");
    }

    return currentUser;
  }, [refreshUser]);

  const register = useCallback(async (form) => {
    await registerClient(form);
    return login(form.email, form.password);
  }, [login]);

  const logout = useCallback(() => {
    setAccessToken(null);
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      login,
      register,
      logout,
      refreshUser,
      isAuthenticated: Boolean(user),
      isAdmin: user?.role === "ADMIN",
      isClient: user?.role === "CLIENT",
    }),
    [user, loading, login, register, logout, refreshUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
