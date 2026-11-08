import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function ClientRoute({ children }) {
  const { isAuthenticated, isClient, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return <div className="page-state">Завантаження...</div>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (!isClient) {
    return <Navigate to={isAdmin ? "/admin" : "/"} replace />;
  }
  return children;
}
