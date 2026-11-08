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

`CustomBouquetBuilder` покроково отримує квіти, упаковку та листівку, після чого створює custom `Bouquet`. `CustomBouquetService` перед Builder перевіряє існування ресурсів і stock.

### Strategy

`DeliveryStrategy` має реалізації `PickupDelivery`, `CourierDelivery`, `ExpressDelivery`.

`DiscountStrategy` має реалізації `NoDiscount`, `GoldDiscount`, `SocialDiscount`, `EventDiscount`, `BonusDiscount`.

Таким чином алгоритм доставки/знижки можна змінити без зміни `OrderService`.

### Decorator

`BouquetComponent` → `BasicBouquet` → `BouquetDecorator`. Реалізації `PackagingDecorator`, `RibbonDecorator`, `GreetingCardDecorator` додають поведінку й ціну без зміни базового об'єкта.

### State

`OrderStateContext` делегує операції поточному стану. Допустимий основний lifecycle:

```text
created -> confirmed -> preparing -> ready -> delivering -> completed
   \            \
    -> cancelled <-
```

Некоректні переходи викликають `InvalidOrderStateTransition`.

### Observer

`NotificationPublisher` повідомляє підписаних observers. `PersistentNotificationObserver` записує події в `notifications`. Observer використовується, зокрема, коли замовлення готове та коли нараховані бонуси.

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
- ADMIN: CRUD каталогу та довідників, усі orders і зміна status.

## 6. Persistence and migrations

SQLAlchemy `Base.metadata` є джерелом ORM-моделі. Alembic використовує ту саму metadata та `DATABASE_URL` із application settings.

Initial migration створює повну схему. Наступні зміни мають оформлюватися новими revisions, а не прямим `create_all()` у production workflow.

## 7. Frontend

React використовує:

- `AuthContext` для сесії/JWT;
- `GuestRoute`, `ProtectedRoute`, `ClientRoute`, `AdminRoute` для UI-level routing;
- окремі API modules для HTTP-запитів;
- `sessionStorage` для checkout draft;
- FastAPI як єдине джерело бізнес-правил і остаточних цін.
