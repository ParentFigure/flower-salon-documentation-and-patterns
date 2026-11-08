# Відповідність вимогам курсової

| Вимога | Реалізація |
|---|---|
| Use Case diagram | `docs/uml/use-case.xml` |
| UML class diagram | `docs/uml/class-diagram.xml` |
| GoF Builder | `app/patterns/builder/custom_bouquet_builder.py` |
| GoF Strategy | `app/patterns/strategy/` |
| GoF Decorator | `app/patterns/decorator/` + production custom-bouquet pricing in `CustomBouquetService` |
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
| Notifications | Observer + persistent notification model/API + automatic NEW_ARRIVAL broadcast + React notification inbox |
| Admin | React `/admin`: orders, flowers, bouquets, packaging, occasions, salons, delivery methods, loyalty + protected REST operations |
| Automated tests | `backend/tests/` |
| Demo data | `backend/scripts/seed_demo.py` |
| Git history | incremental commits for domain, patterns, REST, UI and finalization |

## Варіант 18 — мережа салонів квітів

| Вимога варіанта | Реалізація |
|---|---|
| Букети з каталогу | `Bouquet`, `/api/bouquets`, React `/catalog` |
| Декорування / букет на замовлення | `CustomBouquetBuilder` + production Decorator flow, React `/builder` |
| Пропозиції на весілля, день народження, Валентина, похорони | `Occasion` + фільтрація каталогу |
| Упаковка | `Packaging`, `PackagingDecorator`, admin CRUD |
| Варіації доставки | pickup / courier / express через `DeliveryStrategy` + `DeliveryMethod` |
| Знижки | Gold/Social/Bonus/Event discount strategies; loyalty визначається backend-ом |
| Повідомлення про новинки | admin create bouquet → `NEW_ARRIVAL` → `PersistentNotificationObserver` для всіх клієнтів |
| Повідомлення про готове замовлення | State `ready` → `ORDER_READY` notification |
| Повідомлення про бонуси | loyalty accrual → `BONUS_ACCRUED` notification |
| Gold / bonus / social cards | `LoyaltyCardType`, service/API + React admin loyalty UI |
| Gold: безкоштовна доставка | `LoyaltyService.apply_delivery_benefit()` |
| Персональний кабінет | React `/profile`: profile, loyalty, orders, notification inbox, quick order actions |
| Замовлення | `/catalog` або `/builder` → `/checkout` → `/api/orders` |
| Admin-частина | React `/admin`: orders, flowers, bouquets, packaging, occasions, salons, delivery, loyalty |
