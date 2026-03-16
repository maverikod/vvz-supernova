# search_theory_index.py — Полная документация для ИИ

## Назначение

Инструмент для индексации, поиска и анализа теории из файлов `ALL.md` и `ALL_index.yaml`. Поддерживает работу с YAML-индексом и SQLite-базой для быстрого полнотекстового поиска.

## Архитектура

**Источники данных:**
- `ALL.md` — основной файл теории (234K+ строк)
- `ALL_index.yaml` — структурный индекс блоков (сегментов)
- `ALL_theory_blocks.sqlite` — производная SQLite-база для быстрого поиска

**Принципы:**
- `ALL.md` — единственный источник истины по содержимому
- `ALL_index.yaml` — метаданные (категории, ключевые слова, summaries)
- SQLite — быстрый поисковый слой (FTS5 индексы)
- Скрипт НИКОГДА не изменяет `ALL.md` автоматически

## Структура данных

### YAML индекс (ALL_index.yaml)

```yaml
segments:
  - id: "7d-01"                    # Идентификатор блока
    category: "General"            # Категория
    keywords:                      # Ключевые слова (могут быть строками или числами)
      - "keyword1"
      - "keyword2"
    summary: "Описание блока"      # Краткое описание
    start_line: 151                # Начальная строка
    end_line: 507                  # Конечная строка
    ranges:                        # Множественные диапазоны (опционально)
      - [151, 300]
      - [301, 507]
```

### SQLite база (ALL_theory_blocks.sqlite)

**Таблицы:**
- `segments(id, category, summary, start_line, end_line, text)` — блоки с полным текстом
- `keywords(id, segment_id, keyword)` — ключевые слова
- `formulas(id, segment_id, line, text)` — формулы (строки с `$`, `\(`, `[`)
- `meta(key, value)` — метаданные

**FTS индексы (если доступен FTS5):**
- `segments_fts` — полнотекстовый поиск по блокам
- `formulas_fts` — полнотекстовый поиск по формулам

## Режимы работы

### 1. `stats` — Статистика по индексу

**Назначение:** Получить общую статистику по сегментам.

**Параметры:**
- `--index ALL_index.yaml` (обязательно)
- `--format text|json` (по умолчанию: text)

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode stats
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode stats --format json
```

**Вывод:**
- Общее количество сегментов
- Минимальная/максимальная/средняя длина
- Распределение по категориям

### 2. `validate` — Валидация структуры

**Назначение:** Проверить корректность индекса и соответствие файлу теории.

**Параметры:**
- `--index ALL_index.yaml` (обязательно)
- `--theory ALL.md` (обязательно)
- `--format text|json` (по умолчанию: text)

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --theory ALL.md --mode validate
```

**Проверяет:**
- Наличие ranges для каждого сегмента
- Корректность диапазонов (start_line <= end_line)
- Соответствие диапазонов размеру файла
- Предупреждения о длинных сегментах (>5000 строк)

### 3. `search` — Поиск по YAML индексу

**Назначение:** Найти сегменты по фильтрам (ID, категория, фраза).

**Параметры:**
- `--index ALL_index.yaml` (обязательно)
- `--theory ALL.md` (опционально, для поиска по тексту)
- `--tag "7d-93"` — фильтр по ID (подстрока)
- `--category "галактик"` — фильтр по категории (подстрока)
- `--phrase "CMB"` — поиск по фразе (в keywords, summary, тексте)
- `--preset earth|sun|particles` — быстрые пресеты
- `--format text|json` (по умолчанию: text)

**Примеры:**
```bash
# Поиск по ID
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode search --tag "7d-93"

# Поиск по категории
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode search --category "галактик"

# Поиск по фразе
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --theory ALL.md --mode search --phrase "CMB"

# Использование пресета
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode search --preset earth

# JSON вывод
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode search --phrase "Θ-дефект" --format json
```

**Вывод (text):**
```
7d-93 Глава 7d-93... 216697 234124
```

**Вывод (json):**
```json
[
  {
    "id": "7d-93",
    "category": "...",
    "keywords": [...],
    "summary": "...",
    "start_line": 216697,
    "end_line": 234124,
    "ranges": [[216697, 234124]]
  }
]
```

### 4. `assemble` — Сборка сегментов в файл

**Назначение:** Собрать найденные сегменты в единый markdown файл.

**Параметры:**
- `--index ALL_index.yaml` (обязательно)
- `--theory ALL.md` (обязательно)
- `--output-path path.md` (обязательно)
- Фильтры: `--tag`, `--category`, `--phrase`, `--preset`
- `--format text|json` (только для сообщения о результате)

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --theory ALL.md \
    --mode assemble \
    --phrase "CMB" \
    --output-path cmb_segments.md
```

**Формат вывода:**
```markdown
## [7d-93] Глава 7d-93...
<текст блока из ALL.md>
```

### 5. `tree` — Дерево категорий

**Назначение:** Показать структуру категорий и сегментов.

**Параметры:**
- `--index ALL_index.yaml` (обязательно)
- `--format text|json` (по умолчанию: text)

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode tree
```

**Вывод:**
```
[General] (13 segments)
  - 7d-01 [151-507]
  - 7d-02 [524-878]
...
```

### 6. `sqlite_build` — Построение SQLite базы

**Назначение:** Создать/пересоздать SQLite базу из YAML индекса и файла теории.

**Параметры:**
- `--index ALL_index.yaml` (обязательно)
- `--theory ALL.md` (обязательно)
- `--db-path path.sqlite` (обязательно)

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --theory ALL.md \
    --mode sqlite_build \
    --db-path ALL_theory_blocks.sqlite
```

**Что делает:**
- Удаляет существующую базу (если есть)
- Создает таблицы: segments, keywords, formulas, meta
- Создает FTS индексы (если доступен FTS5)
- Заполняет данными из индекса и файла

**Время выполнения:** ~10-30 секунд для 234K строк

### 7. `sqlite_search` — Полнотекстовый поиск по SQLite

**Назначение:** Быстрый поиск по SQLite базе с использованием FTS индексов.

**Параметры:**
- `--index ALL_index.yaml` (обязательно, для совместимости)
- `--db-path path.sqlite` (обязательно)
- `--phrase "текст"` (обязательно)
- `--scope segments|formulas` (по умолчанию: segments)
- `--tag "7d-93"` — дополнительный фильтр по ID
- `--category "галактик"` — дополнительный фильтр по категории
- `--format text|json` (по умолчанию: text)

**Примеры:**
```bash
# Поиск по блокам
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_search \
    --db-path ALL_theory_blocks.sqlite \
    --phrase "фрактальная" \
    --scope segments

# Поиск по формулам
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_search \
    --db-path ALL_theory_blocks.sqlite \
    --phrase "omega" \
    --scope formulas

# С фильтрами
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_search \
    --db-path ALL_theory_blocks.sqlite \
    --phrase "CMB" \
    --category "фон" \
    --format json
```

**Вывод (text, segments):**
```
[7d-93] Глава 7d-93... :: Микроволновой фон...
<первые 400 символов текста>
----
```

**Вывод (text, formulas):**
```
[7d-01] General :: $\omega^2=c_\phi^2 k^2 + m_\phi^2$
```

**Производительность:** ~0.1 секунды для поиска по всей базе

### 8. `sqlite_export_md` — Экспорт All.md из SQLite

**Назначение:** Экспортировать все блоки из SQLite базы в markdown файл.

**Параметры:**
- `--db-path path.sqlite` (обязательно)
- `--output-path path.md` (обязательно)

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_export_md \
    --db-path ALL_theory_blocks.sqlite \
    --output-path exported_all.md
```

**Формат вывода:**
```markdown
---
%%7d-00%%
---
<текст блока>

---
%%7d-01%%
---
<текст блока>
```

**Примечание:** Блоки сортируются по ID. Между блоками — одна пустая строка.

### 9. `sqlite_export_yaml` — Экспорт YAML индекса из SQLite

**Назначение:** Экспортировать минимальный YAML индекс из SQLite базы.

**Параметры:**
- `--db-path path.sqlite` (обязательно)
- `--output-path path.yaml` (обязательно)

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_export_yaml \
    --db-path ALL_theory_blocks.sqlite \
    --output-path exported_index.yaml
```

**Формат вывода:**
```yaml
segments:
  - id: "7d-01"
    category: "General"
    summary: "..."
    start_line: 151
    end_line: 507
    ranges:
      - [151, 507]
    keywords:
      - "keyword1"
      - "keyword2"
```

**Примечание:** Диапазоны восстанавливаются упрощённо (один отрезок [start_line, end_line]).

### 10. `help` — Справка

**Назначение:** Показать краткую справку по использованию.

**Примеры:**
```bash
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode help
```

## Технические детали

### Кэширование

Скрипт автоматически создает `.pkl` файл рядом с YAML индексом для ускорения загрузки. Кэш обновляется при изменении файла (по mtime и size).

### Обработка ошибок

**Типичные ошибки:**
- `TypeError: sequence item X: expected str instance, int found` — исправлено: keywords преобразуются в строки
- `ERROR: --index is required` — не указан обязательный параметр
- `ERROR: SQLite db not found` — база не существует
- `WARNING: FTS5 not available` — FTS индексы недоступны, используется LIKE

### Производительность

- Загрузка YAML индекса: ~0.1-0.5 сек (с кэшем: ~0.01 сек)
- Поиск по YAML: ~0.5-2 сек (зависит от размера файла)
- Поиск по SQLite: ~0.1 сек (независимо от размера)
- Построение SQLite базы: ~10-30 сек для 234K строк

### Форматы вывода

**text:** Человекочитаемый формат, удобен для просмотра в терминале.

**json:** Машинночитаемый формат, удобен для интеграции с другими инструментами и ИИ.

## Типичные сценарии использования

### Сценарий 1: Быстрый поиск по теории

```bash
# 1. Построить базу (один раз)
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --theory ALL.md \
    --mode sqlite_build \
    --db-path ALL_theory_blocks.sqlite

# 2. Искать по базе
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_search \
    --db-path ALL_theory_blocks.sqlite \
    --phrase "искомый текст"
```

### Сценарий 2: Анализ структуры теории

```bash
# Статистика
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode stats

# Дерево категорий
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --mode tree

# Валидация
python docs/search/engine/search_theory_index.py --index ALL_index.yaml --theory ALL.md --mode validate
```

### Сценарий 3: Извлечение связанных блоков

```bash
# Найти все блоки про CMB
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --theory ALL.md \
    --mode assemble \
    --phrase "CMB" \
    --output-path cmb_blocks.md
```

### Сценарий 4: Поиск формул

```bash
# Найти все формулы с omega
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_search \
    --db-path ALL_theory_blocks.sqlite \
    --phrase "omega" \
    --scope formulas \
    --format json
```

## API для программирования

### Использование как модуль

```python
from search_theory_index import load_index, IndexData, Segment

# Загрузка индекса
idx = load_index("ALL_index.yaml")

# Доступ к сегментам
for seg in idx.segments:
    print(f"{seg.id}: {seg.category}")
    print(f"  Keywords: {seg.keywords}")
    print(f"  Range: {seg.start_line}-{seg.end_line}")
```

### Структуры данных

**Segment:**
- `id: str` — идентификатор блока
- `category: str` — категория
- `keywords: List[str]` — ключевые слова
- `summary: str` — описание
- `start_line: int` — начальная строка
- `end_line: int` — конечная строка
- `ranges: List[Tuple[int, int]]` — множественные диапазоны
- `length: int` — длина сегмента (property)

**IndexData:**
- `segments: List[Segment]` — список сегментов
- `raw: Dict[str, Any]` — сырые данные YAML

## Ограничения и известные проблемы

1. **Размер файлов:** Скрипт оптимизирован для больших файлов (100K+ строк), но может быть медленным на очень больших (>1M строк).

2. **FTS5:** Требует SQLite с поддержкой FTS5. Если недоступен, используется LIKE (медленнее).

3. **Кодировка:** Все файлы должны быть в UTF-8.

4. **Память:** Загрузка всего файла теории в память может быть проблемой для очень больших файлов (>500MB).

## Расширение функционала

Для добавления новых режимов:

1. Создать функцию `mode_new_mode(...) -> int`
2. Добавить обработку в `main()`:
   ```python
   if args.mode == "new_mode":
       return mode_new_mode(...)
   ```
3. Обновить help и документацию

## Версия

Текущая версия: 2.0 (с поддержкой SQLite и исправленными багами)

**Исправления:**
- TypeError в matches_phrase() — keywords преобразуются в строки
- Подключены режимы sqlite_export_md и sqlite_export_yaml
- Улучшена обработка ошибок в sqlite_search

