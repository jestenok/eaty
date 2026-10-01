# eaty

Помогает решить, что поесть:

- **Веб-приложение (на телефоне на кухне):** рецепты на каждый день с таймером на
  каждый шаг, план на неделю, список покупок с ценами из Wolt и учёт продуктов дома.
  Заказы из Wolt попадают туда сами через расширение для Chrome.
- **CLI:** открытые рестораны Wolt не дальше 1 км с хорошим рейтингом.

Стек: FastAPI, SQLAlchemy 2 (async, asyncpg), Alembic, PostgreSQL. Фронтенд — статический SPA
без сборки (`src/static`).

## Структура

Как в остальных сервисах: `API Route → Service → Repository → Model`.

```
src/
  main.py            точка входа: python src/main.py (в Docker: python3 /app/src/main.py)
  server.py          create_app(): lifespan (миграции, сид, клиенты), роутеры, статика
  config.py          настройки eaty поверх core/config.py, всё из окружения
  api/
    routers.py       карта роутов: /api/v1/...
    dependencies.py  composition root: сессия -> репозитории -> сервисы
    v1/              тонкие роутеры: принять запрос, вызвать сервис
  app/
    models/          ORM, модель на файл
    schemas/         Pydantic: *In — вход, *Out — выход
    repositories/    доступ к данным
    service/         бизнес-логика (+ shopping_calculator — чистый расчёт корзины)
    clients/         внешние API: каталог Wolt (async), рестораны Wolt (для CLI)
    utils/           единицы измерения, сопоставление названий
  core/
    db/              Database (движок + единица работы), Base, миграции из кода
    repository/      BaseRepository
    service/         BaseService
    fastapi/         зависимости (сессия), middleware
    error/           ошибки приложения и их HTTP-ответы
  data/recipes.py    встроенные продукты, рецепты (на 2 порции) и меню недели
  migrations/        Alembic
  cli/               выбор ресторана рядом
  static/            SPA
extension/           расширение Chrome: заказы с wolt.com -> приложение
```

### Правила, на которых держится архитектура

- **Транзакция одна на запрос, и коммитит её не сервис.** `get_session` открывает
  `Database.transaction()`: если обработчик отработал, транзакция коммитится, если упал —
  откатывается. Репозитории делают только `flush`, сервисы не открывают и не закрывают
  транзакции. Поэтому несколько сервисов в одном запросе (например, «приготовлено»: план
  + списание продуктов) либо проходят вместе, либо не проходят совсем.
- **Коммит до ответа.** Сессия подключена через `Depends(get_session, scope="function")`:
  коммит происходит, когда обработчик вернул результат, но *до* отправки ответа. С обычным
  scope FastAPI закрыл бы зависимость уже после ответа, и клиент получил бы «200 OK» даже
  при упавшем коммите.
- **Зависимости приходят снаружи.** Сервис получает репозитории и другие сервисы в
  конструкторе. Собираются они в одном месте, `api/dependencies.py`, через `Depends`.
  Глобальных синглтонов нет: `Database`, клиент Wolt и фоновая задача создаются в
  `create_app`/lifespan и лежат в `app.state`. В тестах любое звено подменяется через
  `app.dependency_overrides` или передачей своей `Database` в `create_app`.
- **Фоновая работа сама владеет транзакциями.** Обновление цен идёт без запроса, поэтому
  `CatalogRefreshJob` открывает транзакцию на каждый продукт. Сервис ей тоже собирает
  фабрика из `api/dependencies.py`.
- **Сервисы отдают схемы, а не ORM-объекты**, поэтому после коммита ничего не
  догружается лениво.

## Запуск

```bash
python -m venv .venv
.venv\Scripts\pip install -r requirements-dev.txt
```

`.env` (в git не попадает):

```ini
ENV=local                                            # перезагрузка при правках, адрес 127.0.0.1
POSTGRES_URI=postgresql+asyncpg://user:password@host:port   # сервер, без имени базы
DB_NAME=eaty
# или целиком: DATABASE_URL=postgresql+asyncpg://user:password@host:port/eaty
```

Ещё есть `PORT` (8000), `HOST`, `WOLT_CITY` (batumi), `MIGRATE_ON_START` (true),
`DEBUG`, `ECHO_SQL`. Без `ENV` сервис ведёт себя как в проде: слушает `0.0.0.0`, без перезагрузки.

Базу один раз создать на сервере (psql спросит пароль):

```bash
psql -h <host> -p <port> -U <user> -d postgres -c "create database eaty"
```

Запуск. Миграции и встроенные рецепты накатываются при старте:

```bash
.venv\Scripts\python src/main.py
```

Открыть http://localhost:8000, документация API — http://localhost:8000/api/v1/docs.

Миграции вручную, из корня: `alembic upgrade head`, новая после правки моделей —
`alembic revision --autogenerate -m "что поменялось"`, сверка моделей со схемой — `alembic check`.

### Docker

`Dockerfile` ставит `requirements.txt`, копирует `src/` и запускает `src/main.py`. Настройки
передаются переменными окружения (см. выше). В GitLab образ собирает `.gitlab-ci.yml` на
каждый пуш в `main`.

### С телефона

Локально приложение слушает только `127.0.0.1`. На телефон его удобно отдать через Tailscale
(HTTPS, только в твою сеть) — тогда экран не гаснет во время таймеров и приходят уведомления:

```bash
tailscale serve --bg 8000
```

### Расширение для заказов из Wolt

1. `chrome://extensions` → «Режим разработчика» → «Загрузить распакованное» → папка `extension`.
2. Если приложение не на `http://localhost:8000`, впиши адрес в окошке расширения.
3. Открой на wolt.com историю заказов или заказ — продукты попадут в «Дома».

Расширение не читает cookie и токены: оно смотрит на данные, которые сайт Wolt сам загружает
для страницы заказа, находит в них заказ и отправляет его в приложение без адресов и
телефонов. Разбор сделан по форме данных, корзины и отменённые заказы пропускаются, повторная
отправка ничего не удваивает.

## CLI: рестораны рядом

```bash
cd src
python -m cli --surprise
```

Флаги: `--tag sushi`, `--min-score 8.5`, `--radius 1.5`, `--address "…"`, `--json`.
Координаты в `.env`: `EATY_LAT`, `EATY_LON` (или `EATY_ADDRESS`).

## Тесты

```bash
pytest                              # без базы тесты с БД пропускаются
node --test tests/extract.test.mjs  # разбор заказов в расширении
```

Тесты с базой (миграции, сид, API, откат транзакции) идут при заданном `TEST_DATABASE_URL`.
База **стирается**, поэтому нужен локальный сервер или база с `test` в имени. Без установки
Postgres его можно поднять в памяти через PGlite:

```bash
npx -p @electric-sql/pglite-socket -p @electric-sql/pglite pglite-server --db=memory:// --port=5499 --max-connections=8
set TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5499/postgres
pytest
```

С PGlite нужен драйвер psycopg (asyncpg с ним не работает), с настоящим сервером подходят оба.
