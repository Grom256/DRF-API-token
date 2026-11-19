# Bookstore API — автентифікація і захист

> Цей файл — **шаблон вашого звіту**. Заповніть розділи нижче і закомітьте разом із кодом.
> Умова завдання — у Moodle.

## Варіант

- Номер варіанта: **3**
- Схема: **Token**
- Право: **P3**
- Throttle: **10** запитів/год для аноніма · **200** запитів/добу для користувача
- Інтеграція: **I3**
- Відеозахист (до 3 хв): <посилання>

## Запуск

```bash
python3 -m venv venv              # Windows: py -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed             # автори, 30 книг, користувачі й групи
python manage.py runserver
python manage.py test
```

Тестові користувачі (`python manage.py seed`), пароль `pass12345`:

| Користувач | Пошта | Акаунт | Група / роль |
|---|---|---|---|
| alice | alice@kpi.edu.ua | 30 днів | Editors, власниця третини книг |
| bob | bob@lnu.edu.ua | 30 днів | Editors |
| carol | carol@gmail.com | 30 днів | — |
| newbie | newbie@kpi.edu.ua | щойно | Editors |
| moder | moder@gmail.com | 30 днів | Moderators |
| staff | staff@gmail.com | 30 днів | `is_staff` |
| admin | admin@example.com | — | суперкористувач, пароль `admin` |

## Результат тестів

Вставте останні рядки `python manage.py test`:

```text
Ran 59 tests in 32.696s

OK (skipped=36)
Destroying test database for alias 'default'...
Found 59 test(s).
System check identified no issues (0 silenced).
```

## Журнал `curl -i`

Для кожного пункту — команда і **перші рядки** відповіді (статус і важливі заголовки).

### 1. Вхід і вихід

- **Вхід користувача (отримання токена):**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "pass12345"}'
```
```http
HTTP/1.1 200 OK
Content-Type: application/json
Vary: Accept

{"token":"7ed5f3f7a8639d9d18461a44b219510d01916897"}
```

- **Вихід (відкликання / видалення токена):**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/auth/token/logout/ \
  -H "Authorization: Token 7ed5f3f7a8639d9d18461a44b219510d01916897"
```
```http
HTTP/1.1 204 No Content
Vary: Accept
```

- **Спроба повторного запиту зі старим токеном після виходу:**
```bash
curl -i http://127.0.0.1:8000/api/v1/books/ \
  -H "Authorization: Token 7ed5f3f7a8639d9d18461a44b219510d01916897"
```
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Token
Content-Type: application/json

{"detail":"Недійсний токен."}
```

### 2. Право доступу: дозволено і заборонено

- **Дозволено: створення книги авторизованим користувачем:**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/books/ \
  -H "Authorization: Token 7ed5f3f7a8639d9d18461a44b219510d01916897" \
  -H "Content-Type: application/json" \
  -d '{"title": "Тигролови", "price": "180.00", "author": 1}'
```
```http
HTTP/1.1 201 Created
Content-Type: application/json
Vary: Accept

{"id":31,"title":"Тигролови","author":1,"price":"180.00","cover":null,"owner":"alice"}
```

- **Дозволено: редагування книги її власником (alice):**
```bash
curl -i -X PATCH http://127.0.0.1:8000/api/v1/books/3/ \
  -H "Authorization: Token 7ed5f3f7a8639d9d18461a44b219510d01916897" \
  -H "Content-Type: application/json" \
  -d '{"title": "Оновлена назва"}'
```
```http
HTTP/1.1 200 OK
Content-Type: application/json
Vary: Accept

{"id":3,"title":"Оновлена назва","author":1,"price":"250.00","cover":null,"owner":"alice"}
```

- **Дозволено: редагування книги модератором (moder):**
```bash
curl -i -X PATCH http://127.0.0.1:8000/api/v1/books/3/ \
  -H "Authorization: Token 3a2c7b5f104d9c028e4e9418ad846dd0e4bbdfc6" \
  -H "Content-Type: application/json" \
  -d '{"title": "Зміна від модератора"}'
```
```http
HTTP/1.1 200 OK
Content-Type: application/json
Vary: Accept

{"id":3,"title":"Зміна від модератора","author":1,"price":"250.00","cover":null,"owner":"alice"}
```

- **Заборонено: неавторизований запит на створення книги:**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/books/ \
  -H "Content-Type: application/json" \
  -d '{"title": "Анонімна книга", "price": "100.00", "author": 1}'
```
```http
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Token
Content-Type: application/json

{"detail":"Реквізити перевірки достовірності не надані."}
```

- **Заборонено: редагування чужої книги звичайним користувачем (bob на книгу alice):**
```bash
curl -i -X PATCH http://127.0.0.1:8000/api/v1/books/3/ \
  -H "Authorization: Token 8bf39a117d62058e5d0a91176b6b71f9801452a1" \
  -H "Content-Type: application/json" \
  -d '{"title": "Спроба зламати"}'
```
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json
Vary: Accept

{"detail":"У вас нема дозволу робити цю дію."}
```

### 3. Throttling: останній дозволений запит і `429`

- **10-й запит аноніма на публічний ендпоінт (останній дозволений із 10/год):**
```bash
curl -i http://127.0.0.1:8000/api/v1/authors/
```
```http
HTTP/1.1 200 OK
Content-Type: application/json
Vary: Accept

{"count":3,"next":null,"previous":null,"results":[{"id":1,"name":"Леся Українка"}]}
```

- **11-й запит аноніма (перевищення ліміту):**
```bash
curl -i http://127.0.0.1:8000/api/v1/authors/
```
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
Content-Type: application/json

{"detail":"Запит було проігноровано. Expected available in 3600 seconds."}
```

### 4. Інтеграційна вимога

- **Дозволено: завантаження обкладинки власником книги (alice):**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/books/3/cover/ \
  -H "Authorization: Token 7ed5f3f7a8639d9d18461a44b219510d01916897" \
  -F "cover=@cover.png"
```
```http
HTTP/1.1 200 OK
Content-Type: application/json
Vary: Accept

{"cover":"http://127.0.0.1:8000/media/covers/cover.png"}
```

- **Заборонено: завантаження обкладинки модератором (обкладинку змінює тільки власник):**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/books/3/cover/ \
  -H "Authorization: Token 3a2c7b5f104d9c028e4e9418ad846dd0e4bbdfc6" \
  -F "cover=@cover.png"
```
```http
HTTP/1.1 403 Forbidden
Content-Type: application/json
Vary: Accept

{"detail":"У вас нема дозволу робити цю дію."}
```

- **Заборонено: надсилання JSON замість multipart-форми:**
```bash
curl -i -X POST http://127.0.0.1:8000/api/v1/books/3/cover/ \
  -H "Authorization: Token 7ed5f3f7a8639d9d18461a44b219510d01916897" \
  -H "Content-Type: application/json" \
  -d '{"cover": "test.png"}'
```
```http
HTTP/1.1 415 Unsupported Media Type
Content-Type: application/json

{"detail":"Непідтримуваний тип даних \"application/json\" в запиті."}
```

## Журнал помилок

Щонайменше дві помилки, на які ви справді натрапили.

| Що побачили (текст помилки або код) | Причина | Що змінили |
|---|---|---|
| `AssertionError: 'bookstore.permissions' not found in ['rest_framework.permissions']` під час запуску `test_baseline.py` | Було налаштовано тільки глобальний `IsAuthenticatedOrReadOnly` у `settings.py`, але ще не створено кастомний клас прав у `bookstore/permissions.py` та не підключено його в `BookViewSet.permission_classes`. | Створили клас `IsOwnerOrModeratorOrReadOnly` у `bookstore/permissions.py`, що реалізує логіку варіанта P3, і явно задали `permission_classes = [IsOwnerOrModeratorOrReadOnly]` у `BookViewSet`. |
| `AssertionError: 200 != 403 : модератор — не власник` під час тестування інтеграційної дії I3 (`POST /cover/`) | Дія `cover` за замовчуванням успадковувала клас `IsOwnerOrModeratorOrReadOnly` від `BookViewSet`, який дозволяв модераторам змінювати об'єкт. Але за специфікацією I3 обкладинку може редагувати **виключно власник книги** (навіть модератори та адміни повинні отримувати 403). | Створили окремий клас прав `IsOwnerOnly` у `bookstore/permissions.py` (перевірка `obj.owner == request.user`) та явно призначили його в декораторі дії `@action(..., permission_classes=[IsOwnerOnly])`. |

## Дослідницькі питання

Своїми словами, з посиланням на джерело (документація, рядок вихідного коду пакета).

1. **Де фізично зберігаються токени і що станеться, якщо видалити рядок руками в `python manage.py shell`?**  
   Токени зберігаються в реляційній базі даних у таблиці `authtoken_token`, яка створюється моделлю `Token` додатка `rest_framework.authtoken` (вихідний код: `rest_framework/authtoken/models.py`, клас `Token`). Запис містить ключ `key` (первинний ключ, 40-значний hex-рядок), зв'язок `OneToOneField` на модель користувача `User` та дату створення `created`. Якщо видалити рядок руками, наприклад `Token.objects.filter(user__username='alice').delete()`, то під час наступного запиту користувача з заголовком `Authorization: Token <key>` метод `TokenAuthentication.authenticate_credentials(key)` (`rest_framework/authtoken/authentication.py`, рядок ~95) виконає пошук у базі й викличе виняток `Token.DoesNotExist`. DRF перехопить його та поверне клієнту статус `401 Unauthorized` з повідомленням `{"detail": "Недійсний токен."}`.

2. **Подивіться на клас `ObtainAuthToken`: які в нього `throttle_classes`? Що це означає для перебору паролів через ваш `/auth/token/` і як це виправити?**  
   У вихідному коді класу `ObtainAuthToken` (`rest_framework/authtoken/views.py`, рядки 20–35) атрибут `throttle_classes` явно не визначений, тому клас використовує стандартний список `api_settings.DEFAULT_THROTTLE_CLASSES`. Оскільки для входу звертаються анонімні клієнти, діє спільний анонімний ліміт (у нашому випадку — 10 запитів/год). Це створює дві проблеми: по-перше, зловмисник може легко вичерпати ліміт і заблокувати легітимним анонімним користувачам доступ до API (DoS), а по-друге, загальний ліміт не захищає ефективно від цілеспрямованого підбору паролів за окремим обліковим записом. Щоб виправити це, слід створити підклас `ObtainAuthToken` і перевизначити `throttle_classes`, підключивши спеціалізований тротлер (наприклад, `ScopedRateThrottle` або кастомний `LoginRateThrottle`), що веде облік спроб за комбінацією `IP + username` з жорстким лімітом (наприклад, 5 спроб на хвилину).

3. **Токен передається з кожним запитом, але CSRF-захист для нього не потрібен. Чому?**  
   Атака міжсайтової підробки запиту (CSRF) можлива лише тоді, коли браузер **автоматично** додає автентифікаційні дані клієнта (куки сесії `sessionid`) до будь-яких міжсайтових HTTP-запитів, ініційованих сторонніми ресурсами (через HTML-форми, теги `<script>`, тощо). У випадку автентифікації за токеном значення передається в кастомному HTTP-заголовку `Authorization: Token <key>`. Браузери за стандартами безпеки ніколи автоматично не передають сторонні HTTP-заголовки при міжсайтових діях без явного виклику через JavaScript (CORS). Тому сторонній шкідливий сайт фізично не може змусити браузер жертви надіслати цей заголовок. З цієї причини в класі `TokenAuthentication` (на відміну від `SessionAuthentication`) перевірка CSRF не виконується взагалі (документація DRF: Authentication — TokenAuthentication).

4. **У якому порядку DRF перевіряє автентифікацію, права і ліміти? Знайдіть це в методі `APIView.initial()`. Чому анонімний запит, який отримав `401`, не витрачає ліміт аноніма? Як це видно у вашому варіанті?**  
   У вихідному коді `rest_framework/views.py` метод `APIView.initial()` виконує виклики в такій послідовності (рядки 410–415):
   ```python
   self.perform_authentication(request)
   self.check_permissions(request)
   self.check_throttles(request)
   ```
   Тобто:
   1) автентифікація (визначається `request.user`);
   2) перевірка прав доступу (`check_permissions`);
   3) перевірка лімітів (`check_throttles`).  
   Якщо анонімний запит намагається виконати небезпечну або заборонену дію (наприклад, `POST /api/v1/books/`), на етапі `check_permissions` метод `has_permission()` повертає `False`. Оскільки `request.user` не є автентифікованим, DRF негайно викликає `exceptions.NotAuthenticated()` і перериває обробку запиту з кодом `401`. До кроку `check_throttles` виконання взагалі не доходить, тому лічильник у кеші не збільшується.  
   У нашому варіанті це чітко видно: ліміт аноніма (10 запитів/год) встановлений для читання списку авторів `GET /api/v1/authors/` (де права дозволяють доступ, і перевірка доходить до `check_throttles`). Навіть якщо надіслати 50 заборонених запитів `POST /api/v1/books/`, анонім отримає 50 разів `401`, але його ліміт у 10 дозволених запитів на `GET /api/v1/authors/` залишиться повністю невикористаним.

## Якщо користувались ШІ

Використовував ШІ-асистента для консультацій щодо конфігурації параметрів Варіанта №3 та структурування відповідей. На етапі налаштування автентифікації було враховано підказку щодо порядку `DEFAULT_AUTHENTICATION_CLASSES`, де `TokenAuthentication` обов'язково має передувати сесійній автентифікації, щоб виключити повернення помилкового коду `403` замість `401` із заголовком `WWW-Authenticate`. Для вимоги I3 окремо було реалізовано клас прав `IsOwnerOnly`, щоб гарантувати блокування дій для адміністраторів та модераторів.
