# Архітектура Flower Salon Network

## 1. Загальна схема

```text
React / Vite
    |
    | HTTP + JSON + JWT
    v
FastAPI REST routes
    |
    v
Application services
    |
    +--> GoF patterns
    |
    v
Repositories
    |
    v
SQLAlchemy ORM
    |
    v
PostgreSQL
```

Система побудована за шаровим принципом. REST routes відповідають за HTTP-рівень і validation, services — за бізнес-правила, repositories — за доступ до даних, а SQLAlchemy models — за відображення предметної області в БД.

## 2. Основні сутності

- `User` — обліковий запис і роль `CLIENT` / `ADMIN`.
- `Client` — клієнтський профіль.
- `Flower` — квітка, ціна та залишок.
- `Bouquet` — готовий букет каталогу.
- `BouquetItem` — склад готового букета.
- `Occasion` — подія/призначення букета.
- `Packaging` — варіант упаковки.
- `Salon` — фізична точка мережі.
- `DeliveryMethod` — доступний спосіб доставки.
- `Order` / `OrderItem` — замовлення та його позиції.
- `LoyaltyCard` — Gold/Bonus/Social loyalty-картка.
- `Notification` — збережене сповіщення клієнта.

Custom bouquet не публікується в каталозі. Після оформлення його назва, склад, упаковка, листівка та ціна зберігаються в `OrderItem` як snapshot.

## 3. GoF patterns

### Builder

`CustomBouquetBuilder` покроково формує базовий custom `Bouquet` із вибраних квітів. `CustomBouquetService` перевіряє існування ресурсів і stock, а optional-опції після Builder додаються production-ланцюжком Decorator.

### Strategy

`DeliveryStrategy` має реалізації `PickupDelivery`, `CourierDelivery`, `ExpressDelivery`.

`DiscountStrategy` має реалізації `NoDiscount`, `GoldDiscount`, `SocialDiscount`, `EventDiscount`, `BonusDiscount`.

Таким чином алгоритм доставки/знижки можна змінити без зміни `OrderService`.

### Decorator

`BouquetComponent` → `BasicBouquet` → `BouquetDecorator`. У production custom-bouquet flow `PackagingDecorator` та `GreetingCardDecorator` реально формують фінальну ціну й опис; `RibbonDecorator` демонструє таке саме розширення без зміни базового об'єкта.

### State

`OrderStateContext` делегує операції поточному стану. Допустимий основний lifecycle:

```text
created -> confirmed -> preparing -> ready -> delivering -> completed
   \            \
    -> cancelled <-
```

Некоректні переходи викликають `InvalidOrderStateTransition`.

### Observer

`NotificationPublisher` повідомляє підписаних observers. `PersistentNotificationObserver` записує події в `notifications`. Observer використовується, коли замовлення готове, коли нараховані бонуси та коли адміністратор публікує новий готовий букет у каталозі. NEW_ARRIVAL подія зберігається для всіх клієнтів через `PersistentNotificationObserver`.

## 4. Loyalty

Loyalty-логіка визначається backend-ом із фактичної картки клієнта:

- Gold — 10% і безкоштовна стандартна courier-доставка;
- Social — 15%;
- Bonus — списання фактичного bonus balance;
- після завершення замовлення нараховуються бонуси за правилами `LoyaltyService`.

Frontend не може самостійно призначити клієнту Gold/Social знижку.

## 5. Authentication / authorization

JWT формується після login. FastAPI dependencies перевіряють token, active user, роль і ownership.

- public: каталог та довідкові active-ресурси;
- CLIENT: custom bouquet, checkout, власні orders/profile/notifications/loyalty;
- ADMIN: CRUD каталогу та довідників, усі orders і зміна status, керування loyalty-картками та bonus balance.

## 6. Persistence and migrations

SQLAlchemy `Base.metadata` є джерелом ORM-моделі. Alembic використовує ту саму metadata та `DATABASE_URL` із application settings.

Initial migration створює повну схему. Наступні зміни мають оформлюватися новими revisions, а не прямим `create_all()` у production workflow.

## 7. Frontend

React використовує:

- `AuthContext` для сесії/JWT;
- `GuestRoute`, `ProtectedRoute`, `ClientRoute`, `AdminRoute` для UI-level routing;
- окремі API modules для HTTP-запитів;
- `sessionStorage` для checkout draft;
- FastAPI як єдине джерело бізнес-правил і остаточних цін;
- `/profile` показує історію, loyalty і повний список persisted notifications з read/read-all діями;
- `/admin` містить UI для orders, flowers, bouquets, packaging, occasions, salons, delivery methods та loyalty.
