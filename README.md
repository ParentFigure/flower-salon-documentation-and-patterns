# Flower Salon Network

Курсова робота: інформаційна система мережі квіткових салонів.

Система підтримує каталог готових букетів, конструктор власного букета, оформлення замовлень із доставкою або самовивозом, loyalty-картки, бонуси, сповіщення, персональний кабінет клієнта та адміністративну панель.

## Технології

- **Backend:** Python 3.11+ / FastAPI
- **ORM:** SQLAlchemy 2.x
- **Database:** PostgreSQL 16
- **Migrations:** Alembic
- **Authentication:** JWT Bearer
- **Frontend:** React + Vite
- **Tests:** pytest
- **UML:** editable diagrams.net (`docs/uml`)
- **Local infrastructure:** Docker Compose

## Реалізовані GoF-патерни

- **Builder** — `CustomBouquetBuilder`: покрокове створення власного букета.
- **Strategy** — `DeliveryStrategy` та `DiscountStrategy`: розрахунок доставки й знижок.
- **Decorator** — `BouquetDecorator`: упаковка, стрічка та листівка як додаткові опції.
- **State** — `OrderState`: контроль допустимих переходів статусу замовлення.
- **Observer** — `NotificationPublisher` + observers: сповіщення про готовність замовлення, бонуси та новинки.

Архітектура та відповідність вимогам описані в:

- `docs/ARCHITECTURE.md`
- `docs/REQUIREMENTS_TRACEABILITY.md`

## Структура проєкту

```text
flower-salon-fastapi/
├── backend/
│   ├── alembic/              # міграції БД
│   ├── app/
│   │   ├── api/routes/       # REST controllers
│   │   ├── core/             # config/security
│   │   ├── db/               # SQLAlchemy session/base
│   │   ├── models/           # ORM domain models
│   │   ├── patterns/         # GoF patterns
│   │   ├── repositories/     # data access
│   │   ├── schemas/          # Pydantic schemas
│   │   └── services/         # application/business logic
│   ├── scripts/seed_demo.py
│   └── tests/
├── frontend/
│   └── src/
├── docs/
│   └── uml/
├── docker-compose.yml
└── .env.example
```

## 1. Запуск PostgreSQL

Потрібен запущений Docker Desktop.

```powershell
docker compose up -d db
docker compose ps
```

## 2. Налаштування backend

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

За потреби створи `.env` у `backend/` або використовуй стандартні development-значення з `app/core/config.py`.

Приклад `DATABASE_URL`:

```text
postgresql+psycopg://flower_user:flower_password@localhost:5432/flower_salon
```

## 3. Alembic migrations

### Нова/порожня БД

```powershell
cd backend
alembic upgrade head
```

### БД, яку раніше вже створили через `Base.metadata.create_all()`

Якщо таблиці вже існують і відповідають поточним моделям, **не запускай initial `upgrade` поверх них**. Познач поточну схему як уже мігровану:

```powershell
cd backend
alembic stamp head
```

Після цього всі майбутні зміни застосовуються звичайно:

```powershell
alembic upgrade head
```

Корисні команди:

```powershell
alembic current
alembic history
alembic check
```

Для нової зміни моделей:

```powershell
alembic revision --autogenerate -m "describe schema change"
alembic upgrade head
```

## 4. Demo data

```powershell
cd backend
python -m scripts.seed_demo
```

Seed ідемпотентний: його можна запускати повторно без дублювання основних demo-даних.

Demo admin:

```text
Email: admin@bloom.local
Password: Admin123!
```

## 5. Запуск FastAPI

```powershell
cd backend
uvicorn app.main:app --reload
```

- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health check: `http://127.0.0.1:8000/health`

## 6. Запуск React

В іншому терміналі:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: `http://localhost:5173`

Vite проксіює `/api` на `http://127.0.0.1:8000`.

Production build:

```powershell
npm run build
```

## 7. Тести

```powershell
cd backend
python -m pytest -q
```

Тестовий набір покриває ORM-моделі, repositories, services, GoF patterns, authentication/authorization, REST API, custom bouquets, loyalty, notifications та Alembic initial migration.

## Основні можливості

### Клієнт

- реєстрація та login;
- перегляд і фільтрація каталогу;
- створення власного букета;
- вибір упаковки та листівки;
- оформлення доставки або самовивозу;
- автоматичні loyalty-знижки;
- бонусний баланс;
- історія замовлень;
- персональний кабінет;
- сповіщення про готовність замовлення та бонуси.

### Адміністратор

- перегляд усіх замовлень;
- зміна статусу замовлення за допустимим State lifecycle;
- CRUD квітів;
- CRUD готових букетів;
- backend CRUD салонів, способів доставки, упаковок і подій;
- керування loyalty-операціями через захищені REST endpoints.

## REST API

Основні групи endpoint-ів:

```text
/api/auth
/api/bouquets
/api/flowers
/api/occasions
/api/packaging
/api/salons
/api/delivery-methods
/api/orders
/api/loyalty
/api/notifications
/api/profile
```

Повний контракт доступний у Swagger UI.

## UML

Фінальні редаговані діаграми:

- `docs/uml/use-case-final.drawio`
- `docs/uml/class-diagram-final.drawio`

Відкрити можна через diagrams.net: **File → Open From → Device**.

## Безпека

- паролі зберігаються як hash, а не plain text;
- доступ до захищених endpoint-ів здійснюється через JWT Bearer token;
- CLIENT має доступ лише до власних клієнтських ресурсів;
- ADMIN endpoints захищені перевіркою ролі;
- ціни, loyalty-знижки й вартість custom bouquet повторно розраховуються backend-ом, а не довіряються frontend-у.
