import { useEffect, useState } from "react";
import { AuthContext } from "./useAuth";
import { me } from "../services/auth";
import { clearTokens, getToken } from "../utils/token";

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchUser = async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const res = await me();
      setUser(res);
    } catch {
      clearTokens();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    let ignore = false;
    async function load() {
      if (!getToken()) {
        if (!ignore) {
          setUser(null);
          setLoading(false);
        }
        return;
      }
      try {
        const res = await me();
        if (!ignore) {
          setUser(res);
        }
      } catch {
        clearTokens();
        if (!ignore) {
          setUser(null);
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      ignore = true;
    };
  }, []);

  const logout = () => {
    clearTokens();
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        setUser,
        loading,
        fetchUser,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export default AuthProvider;
