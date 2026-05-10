# README_TESTS.md

## Процент покрытия тестами

По результатам запуска тестов с помощью `coverage` достигнуто покрытие TOTAL coverage: 100%.

## Где смотреть итоги тестирования

Результаты можно смотреть в следующих местах:

coverage_report.txt - текстовый отчёт покрытия кода. В нём отображается покрытие по каждому файлу и итоговая строка `TOTAL`.

htmlcov/index.html - HTML-отчёт покрытия. Его можно открыть в браузере. В отчёте видно, какие строки кода были покрыты тестами, а какие нет.

reports/load/locust_report.html - HTML-отчёт нагрузочного тестирования Locust. В нём отображаются количество запросов, время отклика, ошибки и статистика по эндпоинтам.

CSV-файлы со статистикой нагрузочного тестирования:
```text
reports/load/locust_stats_stats.csv
reports/load/locust_stats_failures.csv
reports/load/locust_stats_exceptions.csv
```

## Какие тесты добавлены

Тесты находятся в папке tests/

В проект добавлены следующие группы тестов:

1. Юнит-тесты для проверки функций аутентификации: хеширование паролей, проверка пароля, создание и декодирование JWT-токена.
2. Юнит-тесты для проверки работы с задачами и бизнес-логики.
3. Функциональные тесты API регистрации и авторизации пользователей.
4. Функциональные тесты API задач: создание, получение, изменение и удаление задач.
5. Функциональные тесты HTML-страниц, форм регистрации, входа, личного кабинета и бэклога.
6. Общие фикстуры для тестов: тестовая база данных, клиент FastAPI, подготовка тестового окружения.

## Как запустить обычные тесты

Из корня проекта выполнить:

```powershell
pytest
```
Ожидаемый результат:
```text
37 passed
```
## Как запустить тесты с покрытием

Из корня проекта выполнить:

```powershell
coverage erase
coverage run -m pytest
coverage report -m
```

Чтобы сохранить текстовый отчёт покрытия в файл:

```powershell
coverage report -m > coverage_report.txt
```

Чтобы создать HTML-отчёт покрытия:

```powershell
coverage html -d htmlcov
```

Открыть HTML-отчёт можно командой:

```powershell
start htmlcov/index.html
```

## Как запустить нагрузочное тестирование

Для нагрузочного тестирования сервер FastAPI нужно запустить отдельно.

### Терминал окно 1 - запуск приложения

```powershell
$env:DATABASE_URL="sqlite:///./taskmanager.db"
$env:SECRET_KEY="dev-secret"

python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8081
```

Если порт `8081` занят, можно выбрать другой порт, например `8090`.

### Терминал окно 2 - запуск Locust

```powershell
cd путь\к\taskmanager
.venv\Scripts\Activate.ps1

New-Item -ItemType Directory -Force reports/load

locust -f locustfile.py --headless --users 8 --spawn-rate 4 --run-time 8s `
  --host http://127.0.0.1:8081 `
  --html reports/load/locust_report.html `
  --csv reports/load/locust_stats
```

После завершения теста отчёт будет доступен по пути:

```text
reports/load/locust_report.html
```

Открыть его можно командой:

```powershell
start reports/load/locust_report.html
```