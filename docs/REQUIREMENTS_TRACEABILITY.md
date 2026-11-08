# Відповідність вимогам курсової

| Вимога | Реалізація |
|---|---|
| Use Case diagram | `docs/uml/use-case.xml` |
| UML class diagram | `docs/uml/class-diagram.xml` |
| GoF Builder | `app/patterns/builder/custom_bouquet_builder.py` |
| GoF Strategy | `app/patterns/strategy/` |
| GoF Decorator | `app/patterns/decorator/` |
| GoF State | `app/patterns/state/order_state.py` |
| GoF Observer | `app/patterns/observer/notification_observer.py` |
| Database | PostgreSQL + SQLAlchemy |
| DB migrations | Alembic, `backend/alembic/` |
| REST API | FastAPI routers under `backend/app/api/routes/` |
| Authentication | JWT register/login/me |
| Client cabinet | `/api/profile` + React `/profile` |
| Catalog | `/api/bouquets` + React `/catalog` |
| Custom bouquet | `/api/bouquets/custom` + React `/builder` |
| Ordering | `/api/orders` + React `/checkout` |
| Delivery/pickup | Delivery Strategy + `DeliveryMethod` + `Salon` |
| Loyalty cards / bonuses | Loyalty model/service/API |
| Notifications | Observer + persistent notification model/API |
| Admin | React `/admin` + protected admin REST operations |
| Automated tests | `backend/tests/` |
| Demo data | `backend/scripts/seed_demo.py` |
| Git history | incremental commits for domain, patterns, REST, UI and finalization |
