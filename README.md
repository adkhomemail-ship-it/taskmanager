# Task Manager

Task Manager — веб-приложение на FastAPI для управления личными задачами.  
Пользователь регистрируется, проходит аутентификацию и получает доступ только к собственным задачам.

## Что умеет проект

- регистрация и вход пользователя
- JWT-аутентификация
- доступ только к своим задачам
- создание, просмотр, изменение и удаление задач
- статусы задач: `в ожидании`, `в работе`, `завершено`
- приоритеты задач: `не важно`, `важно`, `критично`
- дедлайн задачи и визуальный прогресс по сроку
- канбан-представление задач
- backlog-представление задач списком
- сортировка, поиск и пагинация

## Архитектура

Проект разделен на несколько слоев:

- `app/main.py`
  Точка входа FastAPI-приложения, подключение роутеров и middleware.

- `app/config.py`
  Загрузка настроек из переменных окружения.

- `app/database.py`
  Подключение к PostgreSQL, SQLAlchemy engine/session, базовый `lifespan`.

- `app/models.py`
  SQLAlchemy-модели пользователей и задач.

- `app/schemas.py`
  Pydantic-схемы для валидации и сериализации данных.

- `app/auth.py`
  Хеширование паролей, создание JWT, получение текущего пользователя.

- `app/routers/auth.py`
  Роуты регистрации и входа, а также HTML-обработчики для главной страницы.

- `app/routers/tasks.py`
  REST API задач, HTML-страницы `/me` и `/backlog`, сортировка, поиск и пагинация.

- `app/templates/`
  HTML-шаблоны интерфейса:
  - `index.html` — главная страница
  - `me.html` — канбан
  - `backlog.html` — список задач

## Модель данных

### User

- `id`
- `username`
- `hashed_password`
- `created_at`

### Task

- `id`
- `title`
- `description`
- `status`
- `priority`
- `created_at`
- `deadline`
- `owner_id`

## Аутентификация

Для API используется JWT.

После успешного логина или регистрации API возвращает:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

Для защищенных API-запросов требуется заголовок:

```http
Authorization: Bearer <access_token>
```

В HTML-интерфейсе токен хранится в cookie.

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

## Параметры задач

Пример тела задачи:

```json
{
  "title": "Подготовить релиз",
  "description": "Проверить changelog и собрать финальную версию",
  "status": "в работе",
  "priority": "критично",
  "deadline": "2026-03-30"
}
```

Допустимые значения:

- `status`
  - `в ожидании`
  - `в работе`
  - `завершено`

- `priority`
  - `не важно`
  - `важно`
  - `критично`

## Сортировка

Для `GET /api/tasks/` доступен query-параметр:

```text
sort_by=title|created_at|deadline|priority
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
- режимы `Все задачи` / `Ближайшие важные`
- сортировка
- поиск по подстроке
- выбор количества задач на странице
- пагинация

## Postman

В проекте есть готовая коллекция:

- [postman_collection.json](./postman_collection.json)

Что входит в коллекцию:

- `Register`
- `Login`
- `List Tasks`
- `Create Task`
- `Get Task By Id`
- `Update Task`
- `Delete Task`

После `Register` или `Login` токен сохраняется в переменную коллекции автоматически.

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
├─ postman_collection.json
├─ requirements.txt
└─ README.md
```
