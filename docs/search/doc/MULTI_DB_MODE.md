---
Author: Vasiliy Zdanovskiy
email: vasilyvz@gmail.com

# Мульти-БД режим поиска

## Описание

Модуль поиска теперь поддерживает **прозрачный поиск по всем частям базы Θ-теории**, разбитой на несколько SQLite-файлов вида `ALL_theory_blocks.chain.part*.sqlite`.

**Принцип**: Один запрос → все базы → один агрегированный результат

## Использование

### Вариант A: Явный glob-паттерн (предпочтительный)

```bash
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_search \
    --db-path-glob "ALL_theory_blocks.chain.part*.sqlite" \
    --query "закон масштаба" \
    --format json
```

### Вариант B: Автодетект chain-режима (обязательный fallback)

Если передать один файл из цепочки:

```bash
python docs/search/engine/search_theory_index.py \
    --index ALL_index.yaml \
    --mode sqlite_search \
    --db-path ALL_theory_blocks.chain.part001.sqlite \
    --query "закон масштаба" \
    --format json
```

Модуль автоматически:
- Распознаёт паттерн `chain.partXXX.sqlite`
- Находит все файлы `chain.part*.sqlite` в той же директории
- Выполняет поиск по всем частям цепочки

## Формат результата

Каждый найденный сегмент содержит:

```json
{
  "segment_id": "7d-105",
  "category": "Scaling",
  "text": "...",
  "score": 1.234,
  "source_db": "/full/path/to/ALL_theory_blocks.chain.part003.sqlite",
  "part_id": "003",
  "db": "ALL_theory_blocks.chain.part003.sqlite"
}
```

**Поля**:
- `source_db`: полный путь к файлу БД (критично для анализа)
- `part_id`: номер части из паттерна `chain.partXXX.sqlite` (если применимо)
- `db`: только имя файла (для обратной совместимости)

## Обработка ошибок

Реализован **fail-soft** режим:
- Ошибка в одной БД **не ломает** поиск в остальных
- Предупреждения выводятся в stderr
- Поиск продолжается по остальным базам

## Ранжирование

- Результаты из всех БД объединяются
- Общее ранжирование применяется **после агрегации**
- Ограничения (`limit`, `offset`) применяются к **общему списку**, а не к каждой БД отдельно

## Совместимость

- ✅ Существующий одиночный режим поиска **не нарушен**
- ✅ Все существующие CLI аргументы работают как прежде
- ✅ JSON формат расширен, но обратно совместим

## Примеры

### Поиск по всем частям цепочки

```bash
# Автодетект
--db-path ALL_theory_blocks.chain.part001.sqlite

# Явный glob
--db-path-glob "ALL_theory_blocks.chain.part*.sqlite"
```

### Поиск с фильтрацией по части

```bash
# Найти все результаты из part003
--db-path-glob "ALL_theory_blocks.chain.part003.sqlite" \
--query "закон масштаба" \
--format json | jq '.[] | select(.part_id == "003")'
```

## Тестирование

1. **Одна база** → поведение без изменений
2. **Несколько `chain.part*.sqlite`**:
   - Поиск по ключу, который есть только в одной части
   - Поиск по ключу, распределённому по нескольким частям
3. **Проверка**:
   - Корректный `source_db`
   - Корректный `part_id`
   - Корректное ранжирование
   - Корректное применение `limit`

