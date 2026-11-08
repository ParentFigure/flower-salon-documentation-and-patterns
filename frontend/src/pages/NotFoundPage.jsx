import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <section className="page-state">
      <h1>404</h1>
      <p>Такої сторінки немає.</p>
      <Link className="button" to="/">На головну</Link>
    </section>
  );
}
