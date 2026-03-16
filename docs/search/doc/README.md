# Θ Theory Search Tool - Инструкция по установке и использованию

**Author:** Vasiliy Zdanovskiy  
**Email:** vasilyvz@gmail.com

## ⚠️ ВАЖНО: Для поиска индекс НЕ НУЖЕН!

**Для режима `sqlite_search` требуется ТОЛЬКО база данных SQLite.**  
Индекс (`--index`) не используется и не нужен. Для других режимов (`assemble`, `search`, `validate`, `sqlite_build`) индекс обязателен.

## ⚠️ База данных — цепочка файлов (поиск по всем частям)

**База не один файл, а цепочка шардов** из-за ограничения размера (каждый файл ≤15 MB):

- `ALL_theory_blocks.chain.part001.sqlite`
- `ALL_theory_blocks.chain.part002.sqlite`
- `ALL_theory_blocks.chain.part003.sqlite`
- `ALL_theory_blocks.chain.part004.sqlite`

**Поиск должен выполняться по всем файлам цепочки.** Используйте один из вариантов:

1. **`--db-dir docs/search/db`** (по умолчанию в этом проекте) — скрипт находит в каталоге все `*.sqlite` (кроме манифеста `*.chain.sqlite`) и ищет по ним.
2. **`--db-path-glob "docs/search/db/ALL_theory_blocks.chain.part*.sqlite"`** — явно указать все части цепочки.
3. **`--db-path docs/search/db/ALL_theory_blocks.chain.part002.sqlite`** — передать любой один файл цепочки: скрипт подхватит все `chain.part*.sqlite` в том же каталоге.

## 📦 Расположение в проекте supernova

В этом проекте инструмент и данные уже разложены в `docs/search/`:

```
docs/search/
├── db/                          # Базы и индекс
│   ├── ALL_theory_blocks.chain.part*.sqlite
│   ├── ALL_theory_blocks.chain.sqlite   # манифест цепочки
│   ├── ALL_index.yaml
│   └── All.md
├── engine/
│   ├── search_theory_index.py   # Главный скрипт
│   └── theory_index/            # Модули поиска
├── doc/                         # Документация (этот файл и др.)
└── README.md                    # Обзор и быстрый старт
```

Запуск **из корня проекта**: `python docs/search/engine/search_theory_index.py ...`

## 🔧 Требования

### Python
- Python 3.8 или выше
- Проверка версии: `python3 --version`

### Зависимости
```bash
pip install pyparsing>=3.0.0
```

Или установите все зависимости из `requirements.txt` (если он включён в архив):
```bash
pip install -r requirements.txt
```

## 🚀 Быстрый старт

### ⚡ Поиск (sqlite_search) — БЕЗ индекса!

**Для режима `sqlite_search` индекс НЕ НУЖЕН!** Требуется только база данных SQLite.

**Пути по умолчанию в проекте:**
- Скрипт: `docs/search/engine/search_theory_index.py`
- Базы данных: `docs/search/db/` (по умолчанию `--db-dir`)

#### 1. Простой поиск (автоматическое сканирование по умолчанию)

```bash
# Из корня проекта. По умолчанию сканируется docs/search/db/
# --index НЕ НУЖЕН для sqlite_search!
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --phrase "закон масштаба" \
    --format text
```

**По умолчанию `--db-dir=docs/search/db`** — скрипт находит все `.sqlite` шарды в этом каталоге.

#### 2. Поиск по одной части цепочки (автоматически подхватываются все части)

```bash
# Указать любой один файл цепочки — скрипт подхватит все part*.sqlite в той же папке
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path docs/search/db/ALL_theory_blocks.chain.part001.sqlite \
    --phrase "закон масштаба" \
    --format text
```

#### 3. Поиск по glob-паттерну (явно все части цепочки)

```bash
# БЕЗ --index! Только базы данных
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path-glob "docs/search/db/ALL_theory_blocks.chain.part*.sqlite" \
    --phrase "топологический заряд" \
    --format json
```

**Примечание:** Для режимов `assemble`, `search`, `validate`, `sqlite_build` нужен полный индекс (`--index ALL_index.yaml`). Для `sqlite_search` индекс не используется вообще.

### 4. Логические запросы (AND/OR/NOT)

```bash
# БЕЗ --index! По умолчанию используется docs/search/db/
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --query "(глюон OR кварк) AND цвет" \
    --format json \
    --limit 5
```

### 5. Поиск по формулам

```bash
# БЕЗ --index!
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path-glob "/path/to/ALL_theory_blocks.chain.part*.sqlite" \
    --phrase "K_*" \
    --scope formulas \
    --format json
```

### 6. Поиск с ранжированием и пагинацией

```bash
# БЕЗ --index!
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path-glob "/path/to/ALL_theory_blocks.chain.part*.sqlite" \
    --phrase "закон" \
    --sort relevance \
    --limit 10 \
    --offset 0 \
    --format json
```

### 7. Экспорт результатов в HTML

```bash
# БЕЗ --index!
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path-glob "/path/to/ALL_theory_blocks.chain.part*.sqlite" \
    --phrase "масштаб" \
    --export-html results.html \
    --limit 20
```

## 📋 Основные режимы работы

### `sqlite_search` — Поиск по SQLite базе

**⚠️ ВАЖНО: Для этого режима индекс НЕ НУЖЕН!** Требуется только база данных.

Быстрый полнотекстовый поиск с поддержкой:
- Простых фраз (`--phrase`)
- Логических запросов (`--query` с AND/OR/NOT)
- Регулярных выражений (`--regex`)
- Поиска по формулам (`--scope formulas`)
- Мульти-БД режима (`--db-path-glob`)

**Пример (БЕЗ --index):**
```bash
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path docs/search/db/ALL_theory_blocks.chain.part001.sqlite \
    --phrase "искомый текст"
```

### `sqlite_build` — Построение базы
**⚠️ Для этого режима индекс ОБЯЗАТЕЛЕН!**
```bash
python docs/search/engine/search_theory_index.py \
    --index docs/search/db/ALL_index.yaml \
    --theory docs/search/db/All.md \
    --mode sqlite_build \
    --db-path docs/search/db/ALL_theory_blocks.chain.part001.sqlite
```

### `assemble` — Сборка сегментов
**⚠️ Для этого режима индекс ОБЯЗАТЕЛЕН!**
```bash
python docs/search/engine/search_theory_index.py \
    --index docs/search/db/ALL_index.yaml \
    --theory docs/search/db/All.md \
    --mode assemble \
    --phrase "CMB" \
    --output-path cmb_blocks.md
```

## 🔍 Формат результатов

### JSON формат
```json
[
  {
    "id": "7d-01",
    "category": "I. Постулаты теории...",
    "summary": "Материя не является...",
    "snippet": "...текст с найденной фразой...",
    "db": "ALL_theory_blocks.chain.part001.sqlite",
    "source_db": "/full/path/to/ALL_theory_blocks.chain.part001.sqlite",
    "part_id": "001"
  }
]
```

### Текстовый формат
```
[id] (database) category :: summary
---
%%id%%
---
<текст блока>
```

## 📚 Дополнительная документация

- **QUICK_REFERENCE.md** — Краткая справка по всем режимам
- **AI_DOCUMENTATION.md** — Полная документация для ИИ-ассистентов
- **MULTI_DB_MODE.md** — Подробное описание мульти-БД режима

## ⚙️ Продвинутые опции

### Регулярные выражения
```bash
--phrase "закон.*масштаб" --regex
```

### Поиск по близости
```bash
--phrase "закон масштаб" --proximity 5
```

### Группировка результатов
```bash
--group-by category
--group-by db
```

### Фильтры по длине
```bash
--min-length 100
--max-length 5000
```

### Подсветка найденных фраз
```bash
--highlight
```

### Контекст вокруг совпадений
```bash
--context 3  # 3 строки до и после
```

## 🐛 Решение проблем

### Ошибка: "ModuleNotFoundError: No module named 'pyparsing'"
```bash
pip install pyparsing>=3.0.0
```

### Ошибка: "No such file or directory: ALL_index.yaml"
Убедитесь, что вы запускаете скрипт из правильной директории или укажите полный путь к индексу:
```bash
--index /full/path/to/ALL_index.yaml
```

### Ошибка: "No database found"
Проверьте путь к базе данных:
```bash
ls -la docs/search/db/ALL_theory_blocks*.sqlite
```

## 📝 Примеры использования

### Найти все упоминания "закон масштаба"
```bash
# БЕЗ --index!
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path-glob "docs/search/db/ALL_theory_blocks.chain.part*.sqlite" \
    --phrase "закон масштаба" \
    --format json > results.json
```

### Найти информацию о глюонах и кварках
```bash
# БЕЗ --index!
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path-glob "docs/search/db/ALL_theory_blocks.chain.part*.sqlite" \
    --query "глюон OR кварк" \
    --format text
```

### Экспортировать результаты в HTML с подсветкой
```bash
# БЕЗ --index!
python docs/search/engine/search_theory_index.py \
    --mode sqlite_search \
    --db-path-glob "docs/search/db/ALL_theory_blocks.chain.part*.sqlite" \
    --phrase "топологический заряд" \
    --highlight \
    --export-html charge_results.html \
    --limit 50
```

## 🔗 Контакты

При возникновении проблем или вопросов обращайтесь:
- Email: vasilyvz@gmail.com

---

**Версия:** 2.0 (с поддержкой мульти-БД режима)  
**Дата:** 2025-01-02

