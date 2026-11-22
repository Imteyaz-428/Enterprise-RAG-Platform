import { Navigate } from "react-router-dom";
import { useAuth } from "../context/useAuth";
import { getToken } from "../utils/token";
import { hasRole } from "../utils/roles";

function ProtectedRoute({ children, minRole }) {
  const token = getToken();
  const { user, loading } = useAuth();

  if (!token) {
    return <Navigate to="/login" replace />;
  }

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gray-50">
        <div className="text-gray-500 font-medium">Loading...</div>
      </div>
    );
  }

  if (minRole && !hasRole(user, minRole)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}

export default ProtectedRoute;
