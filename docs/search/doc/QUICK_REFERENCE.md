# search_theory_index.py — Краткая справка для ИИ

## Базовый синтаксис

```bash
python docs/search/engine/search_theory_index.py \
    --index docs/search/db/ALL_index.yaml \
    --theory docs/search/db/All.md \
    --mode <MODE> \
    [опции]
```

## Режимы работы

### 1. `stats` — Статистика
```bash
--mode stats [--format text|json]
```
Вывод: количество сегментов, распределение по категориям, длины.

### 2. `validate` — Валидация
```bash
--mode validate --theory All.md [--format text|json]
```
Проверяет: корректность ranges, границы файла, длинные сегменты.

### 3. `search` — Поиск по YAML
```bash
--mode search --theory All.md \
    [--tag "7d-93"] \
    [--category "галактик"] \
    [--phrase "CMB"] \
    [--preset earth|sun|particles] \
    [--format text|json]
```
Фильтры: ID (подстрока), категория (подстрока), фраза (в keywords/summary/тексте).

### 4. `assemble` — Сборка сегментов
```bash
--mode assemble --theory All.md --output-path output.md \
    [--tag|--category|--phrase|--preset]
```
Собирает найденные сегменты в markdown файл.

### 5. `tree` — Дерево категорий
```bash
--mode tree [--format text|json]
```
Показывает структуру категорий и сегментов.

### 6. `sqlite_build` — Построение SQLite базы
```bash
--mode sqlite_build --theory All.md --db-path path.sqlite
```
Создаёт/пересоздаёт базу из индекса и файла. Удаляет существующую.

### 7. `sqlite_search` — Поиск по SQLite
```bash
--mode sqlite_search --db-path path.sqlite \
    --phrase "текст" \
    [--scope segments|formulas] \
    [--tag "7d-93"] \
    [--category "галактик"] \
    [--format text|json]
```
Быстрый полнотекстовый поиск (FTS5). scope: segments (блоки) или formulas (формулы).

### 8. `sqlite_export_md` — Экспорт в Markdown
```bash
--mode sqlite_export_md --db-path path.sqlite --output-path output.md
```
Экспортирует все блоки из базы в markdown (формат: `---\n%%id%%\n---\n<текст>`).

### 9. `sqlite_export_yaml` — Экспорт в YAML
```bash
--mode sqlite_export_yaml --db-path path.sqlite --output-path output.yaml
```
Экспортирует минимальный YAML индекс из базы.

### 10. `sqlite_map` — Карта теории
```bash
--mode sqlite_map --db-path path.sqlite \
    [--output-path map.md] \
    [--format text|json]
```
Создаёт карту всей теории (id → тема) автоматически из БД. Выводит список всех сегментов с их ID и категориями.

### 11. `help` — Справка
```bash
--mode help
```

## Типичные сценарии

### Быстрый поиск
```bash
# 1. Построить базу (один раз)
python docs/search/engine/search_theory_index.py \
    --index docs/search/db/ALL_index.yaml \
    --theory docs/search/db/All.md \
    --mode sqlite_build \
    --db-path docs/search/db/

# 2. Искать
python docs/search/engine/search_theory_index.py \
    --index docs/search/db/ALL_index.yaml \
    --mode sqlite_search \
    --db-path docs/search/db/ \
    --phrase "искомый текст"
```

### Поиск формул
```bash
--mode sqlite_search --db-path path.sqlite \
    --phrase "omega" --scope formulas
```

### Извлечение связанных блоков
```bash
--mode assemble --theory All.md \
    --phrase "CMB" --output-path cmb_blocks.md
```

### Использование SQL Views
```bash
# Прямой SQL запрос к представлениям
sqlite3 docs/search/db/ "SELECT id, category FROM view_cells LIMIT 10"
sqlite3 docs/search/db/ "SELECT id, category FROM view_earth LIMIT 10"
sqlite3 docs/search/db/ "SELECT id, category FROM view_driver LIMIT 10"
```

### Создание карты теории
```bash
# Вывод в консоль
--mode sqlite_map --db-path path.sqlite --format text

# Сохранение в файл
--mode sqlite_map --db-path path.sqlite --output-path theory_map.md --format text

# JSON формат
--mode sqlite_map --db-path path.sqlite --output-path theory_map.json --format json
```

## Структура данных

**YAML индекс:**
- `segments`: список блоков
- Каждый блок: `id`, `category`, `keywords`, `summary`, `start_line`, `end_line`, `ranges`

**SQLite база:**
- `segments(id, category, summary, start_line, end_line, text)`
- `keywords(id, segment_id, keyword)`
- `formulas(id, segment_id, line, text)`
- FTS индексы: `segments_fts`, `formulas_fts` (FTS5 используется автоматически)
- **SQL Views (тематические представления):**
  - `view_cells` — всё про ячейки ВБП (29 сегментов)
  - `view_earth` — только Земля (17 сегментов)
  - `view_driver` — всё про драйвер F⊕ (10 сегментов)

## Форматы вывода

- `text`: человекочитаемый формат
- `json`: машинночитаемый формат

## Производительность

- Загрузка YAML: ~0.1-0.5 сек (с кэшем: ~0.01 сек)
- Поиск по YAML: ~0.5-2 сек
- Поиск по SQLite: ~0.1 сек (FTS5 используется автоматически)
- Построение SQLite: ~10-30 сек для 243K строк

## Постоянное поведение для ИИ

**Всегда использовать FTS5 для теоретических выкладок:**
- При поиске по теории используй `sqlite_search` с `--scope segments` (FTS5 включён автоматически)
- Для поиска формул используй `--scope formulas` (FTS5 для формул)
- SQL Views доступны для тематического поиска: `view_cells` (29 сегментов), `view_earth` (17 сегментов), `view_driver` (10 сегментов)
- Карта теории (`sqlite_map`) создаётся автоматически из БД для быстрой навигации (100 сегментов)

**Примеры использования Views:**
```python
import sqlite3
conn = sqlite3.connect('docs/search/db/')
cur = conn.cursor()

# Все про ячейки ВБП
cells = cur.execute("SELECT id, category FROM view_cells").fetchall()

# Только Земля
earth = cur.execute("SELECT id, category FROM view_earth").fetchall()

# Все про драйвер F⊕
driver = cur.execute("SELECT id, category FROM view_driver").fetchall()
```

## Пути файлов

- Индекс: `docs/search/db/ALL_index.yaml`
- Теория: `docs/search/db/All.md`
- База: `docs/search/db/` (38MB, 100 сегментов)
- Скрипт: `docs/search/engine/search_theory_index.py`
- Карта теории: создаётся через `sqlite_map` (например в `docs/search/doc/theory_map.md`)

