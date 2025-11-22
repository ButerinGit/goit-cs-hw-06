# Simple Web App with Socket Server & MongoDB

Навчальний проєкт: простий вебзастосунок на чистому Python (без вебфреймворків), який:

- віддає HTML-сторінки та статичні файли через власний HTTP-сервер;
- приймає дані з форми, пересилає їх на Socket-сервер;
- зберігає повідомлення у базі даних **MongoDB**;
- запускається в Docker-контейнерах через **docker-compose**.

---

## Стек технологій

- **Python** (http.server, socket, multiprocessing)
- **MongoDB** (через бібліотеку `pymongo`)
- **Docker** + **Docker Compose**
- HTML, CSS (статичні ресурси)
- **TCP-сокети** для взаємодії між вебдодатком і Socket-сервером

---

## Структура проєкту

```text
goit-cs-hw-06/
├── main.py                # HTTP-сервер + Socket-сервер (два процеси)
├── Dockerfile
├── docker-compose.yaml
├── requirements.txt
├── data.json              # допоміжний файл із завдання (необов’язковий)
├── templates/
│   ├── index.html         # головна сторінка
│   ├── message.html       # сторінка з формою
│   └── error.html         # сторінка 404
└── static/
    ├── style.css          # стилі
    └── logo.png           # логотип
```

---

## Логіка роботи

1. **HTTP-сервер** працює на `0.0.0.0:3000` і обробляє маршрути:
   - `/` або `/index.html` → `templates/index.html`
   - `/message` або `/message.html` → `templates/message.html`
   - `/style.css` → `static/style.css`
   - `/logo.png` → `static/logo.png`
   - будь-який інший шлях → `templates/error.html` (404)

2. **Форма** на сторінці `message.html`:
   - метод: `POST`
   - action: `/message`
   - поля:
     - `username`
     - `message`

3. Після надсилання форми:
   - HTTP-сервер зчитує дані `username` та `message`;
   - формує словник `{"username": "...", "message": "..."}`;
   - відправляє його як JSON на **Socket-сервер** по TCP (порт `5000`).

4. **Socket-сервер**:
   - слухає `0.0.0.0:5000`;
   - приймає JSON, перетворює в словник;
   - додає поле `date` як час отримання:
     ```python
     datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
     ```
   - зберігає документ у MongoDB в базу `messages_db`, колекцію `messages`.

Формат документа в MongoDB:

```json
{
  "date": "2025-11-17 21:05:49.591388",
  "username": "user_2",
  "message": "message_2"
}
```

---

## Запуск через Docker Compose

### Попередні вимоги

- Встановлені **Docker** та **Docker Compose**.

### Кроки

У корені проєкту:

```bash
docker-compose build
docker-compose up
```

або у фоні:

```bash
docker-compose up -d
```

Після запуску:

- вебдодаток доступний за адресою:  
  **http://localhost:3000**
- MongoDB працює всередині контейнера `mongo`:
  - порт: `27017`
  - дані зберігаються в volume `mongo_data` (не губляться при пересозданні контейнера)

### Перемінні оточення

У `docker-compose.yaml` для сервісу `app` встановлено:

```yaml
environment:
  - MONGO_URI=mongodb://mongo:27017/
```

Це дозволяє Python-додатку підключатися до MongoDB за ім’ям сервісу `mongo` всередині docker-мережі.

---

## Перевірка збережених повідомлень у MongoDB

1. Подивитися, що контейнери працюють:

```bash
docker ps
```

2. Зайти в оболонку MongoDB:

```bash
docker exec -it mongo mongosh
```

3. У консолі `mongosh`:

```javascript
use messages_db
db.messages.find().pretty()
```

Тут будуть усі збережені повідомлення з полями `date`, `username`, `message`.

---

## Локальний запуск без Docker (опційно)

> Для розробки можна запускати застосунок локально, без контейнерів.

### 1. Створити та активувати віртуальне середовище (рекомендовано)

```bash
python -m venv venv
source venv/bin/activate    # macOS / Linux
# або
venv\Scriptsctivate       # Windows
```

### 2. Встановити залежності

```bash
pip install -r requirements.txt
```

### 3. Запустити MongoDB локально

Потрібен локальний інстанс MongoDB (порт `27017` за замовчуванням).  
У такому випадку змінна `MONGO_URI` може бути, наприклад:

```bash
export MONGO_URI="mongodb://localhost:27017/"
```

### 4. Запустити застосунок

```bash
python main.py
```

Після цього вебдодаток буде доступний на:

```text
http://localhost:3000
```

---

## Можливі покращення

- Вивід списку останніх повідомлень на `index.html`.
- Валідація даних форми (обов’язкові поля, обмеження довжини).
- Логування в окремі файли.
- Обробка помилок підключення до MongoDB з відображенням зрозумілих повідомлень користувачу.

---
