import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function GuestRoute({ children }) {
  const { user, loading, isAdmin } = useAuth();

  if (loading) {
    return <div className="page-state">Перевіряємо сесію...</div>;
  }

  if (user) {
    return <Navigate to={isAdmin ? "/admin" : "/profile"} replace />;
  }

  return children;
}
