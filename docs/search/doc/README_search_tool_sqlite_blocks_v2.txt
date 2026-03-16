search_theory_index.py — SQLite + экспорт All.md / YAML
=======================================================

Главное
-------
* Источник истины по содержимому — файл All.md.
* ALL_index.yaml и SQLite-база — производные артефакты.
* Скрипт умеет:
    - строить SQLite-базу по All.md + ALL_index.yaml;
    - делать полнотекстовый поиск по блокам и формулам (FTS, если доступно);
    - экспортировать All.md из SQLite;
    - экспортировать YAML-индекс из SQLite в минимально достаточном виде.

1. Сборка SQLite-базы по All.md + ALL_index.yaml
------------------------------------------------

  python docs/search/engine/search_theory_index.py \\
      --index docs/search/db/ALL_index.yaml \\
      --theory docs/search/db/All.md \\
      --mode sqlite_build \\
      --db-path docs/search/db/ALL_theory_blocks.sqlite

В базе получаем:

  * segments(id, category, summary, start_line, end_line, text)
  * keywords(id, segment_id, keyword)
  * formulas(id, segment_id, line, text)
  * meta(key, value)

  + индексы по полям и (если есть FTS5 в SQLite):

  * segments_fts USING fts5(id, category, summary, text)
  * formulas_fts USING fts5(segment_id, text)

2. Полнотекстовый поиск по базе
-------------------------------

Поиск по чанкам блоков:

  python docs/search/engine/search_theory_index.py \\
      --mode sqlite_search \\
      --db-path docs/search/db/ALL_theory_blocks.chain.part001.sqlite \\
      --phrase "Θ-лест" \\
      --scope segments \\
      --format text

Поиск по формулам:

  python docs/search/engine/search_theory_index.py \\
      --mode sqlite_search \\
      --db-path docs/search/db/ALL_theory_blocks.chain.part001.sqlite \\
      --phrase "\\omega_n" \\
      --scope formulas \\
      --format text

3. Экспорт All.md из SQLite
---------------------------

  python3 search_theory_index.py \\
      --index ALL_index.yaml \\
      --mode sqlite_export_md \\
      --db-path ALL_theory_blocks.sqlite \\
      --output-path All_exported.md

Формат вывода:

  ---
  %%7d-NN%%
  ---
  <текст блока>

Блоки сортируются по id. Между блоками вставляется одна пустая строка.

4. Экспорт YAML-индекса из SQLite
---------------------------------

  python3 search_theory_index.py \\
      --index ALL_index.yaml \\
      --mode sqlite_export_yaml \\
      --db-path ALL_theory_blocks.sqlite \\
      --output-path ALL_index_exported.yaml

Формат YAML (минимально достаточный для поиска):

  segments:
    - id: 7d-01
      category: "..."
      summary:  "..."
      start_line: N1
      end_line:   N2
      ranges:
        - [N1, N2]
      keywords:
        - "..."
        - "..."

Диапазоны восстанавливаются упрощённо: один отрезок [start_line, end_line],
потому что первичная информация по ranges хранится в индексе, а не в SQLite.
При этом сохраняется возможность быстро искать и фильтровать по id/category/keywords.

5. Поведение по источникам
--------------------------

* All.md остаётся единственным источником содержимого теории.
* ALL_index.yaml — структурный индекс (его можно править руками или пересобирать отдельно).
* SQLite — быстрый поисковый слой (поиск, экспорт, выборки для анализа/ML).

Скрипт НИКОГДА не записывает ничего обратно в All.md автоматически.
Экспорт в All_exported.md / ALL_index_exported.yaml — это явная операция
по команде пользователя.
