# Task Manager

Веб-приложение на FastAPI для управления личными задачами с JWT-аутентификацией, PostgreSQL и HTML-интерфейсом.

## Возможности

- регистрация и вход пользователя
- JWT-аутентификация
- доступ только к собственным задачам
- CRUD для задач
- статусы задач: `в ожидании`, `в работе`, `завершено`
- приоритеты задач: `не важно`, `важно`, `критично`
- дедлайн задачи и прогресс по сроку
- канбан-страница `/me`
- страница бэклога `/backlog`
- поиск по подстроке в названии и/или описании задачи
- сортировка задач
- пагинация на странице бэклога
- Postman collection для API

## Стек

- FastAPI
- SQLAlchemy 2
- PostgreSQL
- Jinja2
- JWT (`python-jose`)
- хеширование паролей через `passlib`

## Структура проекта

```text
taskmanager/
├─ app/
│  ├─ routers/
│  │  ├─ auth.py
│  │  └─ tasks.py
│  ├─ templates/
│  │  ├─ index.html
│  │  ├─ me.html
│  │  └─ backlog.html
│  ├─ auth.py
│  ├─ config.py
│  ├─ database.py
│  ├─ main.py
│  ├─ models.py
│  └─ schemas.py
├─ .env.example
├─ postman_collection.json
├─ requirements.txt
└─ README.md
```

## Запуск

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Создайте файл `.env` на основе `.env.example`.

Пример:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/taskmanager
SECRET_KEY=dev-secret-key-change-this-before-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

3. Создайте базу данных PostgreSQL `taskmanager`.

4. Запустите приложение:

```bash
python -m uvicorn app.main:app --reload
```

5. Откройте в браузере:

```text
http://127.0.0.1:8000
```

## Деплой на сервер

В проект уже добавлены файлы для запуска в Docker:

- [Dockerfile](./Dockerfile)
- [docker-compose.yml](./docker-compose.yml)
- [.dockerignore](./.dockerignore)
- [.env.docker.example](./.env.docker.example)
- [deploy/nginx.conf](./deploy/nginx.conf)

### Вариант через Docker Compose

1. Установите на сервер:

- Docker
- Docker Compose plugin

2. Скопируйте проект на сервер.

3. Создайте `.env` на основе `.env.docker.example`:

```env
POSTGRES_DB=taskmanager
POSTGRES_USER=postgres
POSTGRES_PASSWORD=change-me
SECRET_KEY=change-me-before-production
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

4. Соберите и поднимите контейнеры:

```bash
docker compose up -d --build
```

5. Проверьте состояние:

```bash
docker compose ps
docker compose logs -f app
```

6. Приложение будет доступно на:

```text
http://SERVER_IP:8000
```

### Обновление приложения на сервере

После нового пуша и `git pull`:

```bash
docker compose down
docker compose up -d --build
```

### PostgreSQL в Docker

В `docker-compose.yml` база запускается отдельным контейнером:

- данные хранятся в volume `postgres_data`
- приложение подключается к БД по хосту `db`
- таблицы создаются автоматически при старте приложения

### Nginx

В проект добавлен пример reverse proxy:

- [deploy/nginx.conf](./deploy/nginx.conf)

Его можно использовать, если ты хочешь:

- публиковать приложение через `80/443`
- поставить SSL через Certbot
- не открывать наружу порт `8000`

### Что рекомендуется для production

- заменить `SECRET_KEY`
- задать сильный пароль PostgreSQL
- ограничить доступ к серверу по firewall
- ставить приложение за Nginx
- подключить HTTPS
- использовать регулярные бэкапы PostgreSQL
- перейти с `create_all` на Alembic-миграции

## Настройка PostgreSQL

Приложение ожидает локальную PostgreSQL-базу.

Минимально нужно:

1. установить PostgreSQL
2. создать базу `taskmanager`
3. указать корректный логин и пароль в `.env`

Если база уже была создана до добавления новых полей, может потребоваться ручное обновление схемы.

Пример SQL для актуализации таблицы `tasks`:

```sql
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS deadline DATE;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'task_priority') THEN
        CREATE TYPE task_priority AS ENUM ('не важно', 'важно', 'критично');
    END IF;
END
$$;

ALTER TABLE tasks
ADD COLUMN IF NOT EXISTS priority task_priority NOT NULL DEFAULT 'не важно';
```

## Аутентификация

Для API используется JWT.

После логина или регистрации API возвращает:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

Во все защищенные API-запросы нужно передавать:

```http
Authorization: Bearer <access_token>
```

В HTML-интерфейсе токен сохраняется в cookie.

## REST API

### Auth

- `POST /api/auth/register`
- `POST /api/auth/login`

### Tasks

- `GET /api/tasks/`
- `POST /api/tasks/`
- `GET /api/tasks/{task_id}`
- `PUT /api/tasks/{task_id}`
- `DELETE /api/tasks/{task_id}`

### Параметры сортировки

Для `GET /api/tasks/` доступен query-параметр:

```text
sort_by=title|created_at|deadline|priority
```

## Пример задачи

```json
{
  "title": "Подготовить релиз",
  "description": "Проверить changelog и собрать финальную версию",
  "status": "в работе",
  "priority": "критично",
  "deadline": "2026-03-30"
}
```

## Интерфейс

### Главная страница

- регистрация
- вход

### `/me`

- канбан по статусам
- создание задачи
- редактирование задачи
- изменение статуса переносом карточки

### `/backlog`

- список широких карточек
- сортировка
- поиск
- режимы `Все задачи` / `Ближайшие важные`
- пагинация

## Postman

В проекте уже есть готовая коллекция:

- [postman_collection.json](./postman_collection.json)

Импортируйте ее в Postman и задайте:

- `base_url = http://127.0.0.1:8000`

После `Register` или `Login` токен автоматически сохранится в переменную коллекции.

## Замечания

- таблицы создаются автоматически через `lifespan`, но существующие таблицы не мигрируются автоматически
- для production лучше использовать миграции, например Alembic
- `.env` не должен попадать в Git

## Git

Для проекта уже подготовлен `.gitignore`, который исключает:

- `.env`
- `__pycache__`
- `*.pyc`
- виртуальные окружения
- служебные файлы IDE
