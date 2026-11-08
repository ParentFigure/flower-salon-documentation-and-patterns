import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

function navClass({ isActive }) {
  return isActive ? "nav-link active" : "nav-link";
}

export default function Layout() {
  const { user, isAdmin, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/", { replace: true });
  }

  return (
    <div className="app-shell">
      <header className="site-header">
        <NavLink className="brand" to="/">Bloom Network</NavLink>
        <nav className="site-nav" aria-label="Головна навігація">
          <NavLink className={navClass} to="/catalog">Каталог</NavLink>
          {user && <NavLink className={navClass} to="/profile">Кабінет</NavLink>}
          {isAdmin && <NavLink className={navClass} to="/admin">Адмін</NavLink>}
          {!user ? (
            <>
              <NavLink className={navClass} to="/login">Увійти</NavLink>
              <NavLink className="button small" to="/register">Реєстрація</NavLink>
            </>
          ) : (
            <button className="button ghost small" type="button" onClick={handleLogout}>
              Вийти
            </button>
          )}
        </nav>
      </header>
      <main className="site-main">
        <Outlet />
      </main>
      <footer className="site-footer">Flower Salon Network · course project</footer>
    </div>
  );
}
