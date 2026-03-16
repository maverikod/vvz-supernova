search_theory_index.py + SQLite/FTS
===================================

Что делает
----------
Скрипт читает:
  * ALL_index.yaml — индекс блоков (%%7d-NN%%);
  * All.md         — полный текст теории;

и может собрать по ним **SQLite-базу**, в которой:

  * каждый блок %%7d-NN%% хранится как отдельный чанк текста;
  * есть таблица формул (строки с '$', '\\(' или '\\[');
  * построены индексы по категориям, ключевым словам и формульным строкам;
  * при наличии модуля FTS5 создаются полнотекстовые индексы (FTS)
    по чанкам и по формулам.

Структура базы
--------------
При запуске `--mode sqlite_build` создаётся/пересоздаётся база с таблицами:

  * meta(key TEXT PRIMARY KEY, value TEXT)
  * segments(
        id         TEXT PRIMARY KEY,    -- например '7d-64'
        category   TEXT,
        summary    TEXT,
        start_line INTEGER,
        end_line   INTEGER,
        text       TEXT                 -- ЧАНК текста блока (все ranges)
    )
  * keywords(
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        segment_id TEXT,                -- '7d-64'
        keyword    TEXT
    )
  * formulas(
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        segment_id TEXT,
        line       INTEGER,             -- номер строки в All.md
        text       TEXT                 -- строка с формулой
    )

Индексы:
  * idx_segments_category ON segments(category)
  * idx_keywords_keyword  ON keywords(keyword)
  * idx_keywords_segment  ON keywords(segment_id)
  * idx_formulas_segment  ON formulas(segment_id)

Полнотекстовые индексы (если FTS5 доступен в SQLite):
  * segments_fts USING fts5(id, category, summary, text)
  * formulas_fts USING fts5(segment_id, text)

Таким образом, в базе есть:
  * чанк текста на каждый блок %%7d-NN%% (segments.text);
  * связка id/category/summary/keywords;
  * полная коллекция формульных строк, привязанная к блокам;
  * B-tree индексы по категориям, ключевым словам и формульным строкам;
  * FTS-индексы для полнотекстового поиска.

Режимы, связанные с SQLite
--------------------------

1) Сборка базы: sqlite_build
   -------------------------

   Пример:

     python3 search_theory_index.py \\
         --index ALL_index.yaml \\
         --theory All.md \\
         --mode sqlite_build \\
         --db-path ALL_theory_blocks.sqlite

   Комментарии:

     * Если ALL_theory_blocks.sqlite существует — удаляется и создаётся заново.
     * Для каждого сегмента из ALL_index.yaml:
         - формируется текст чанка (все ranges блока);
         - пишется запись в segments;
         - пишутся ключевые слова в keywords;
         - вынимаются формульные строки (по токенам '$', '\\(', '\\[')
           и пишутся в formulas (+ formulas_fts, если доступен FTS);
         - при наличии FTS создаётся запись в segments_fts.

2) Полнотекстовый поиск: sqlite_search
   -----------------------------------

   Пример поиска по чанкам блоков:

     python3 search_theory_index.py \\
         --index ALL_index.yaml \\
         --mode sqlite_search \\
         --db-path ALL_theory_blocks.sqlite \\
         --phrase "Θ-лест" \\
         --scope segments \\
         --format text

   Пример поиска по формулам:

     python3 search_theory_index.py \\
         --index ALL_index.yaml \\
         --mode sqlite_search \\
         --db-path ALL_theory_blocks.sqlite \\
         --phrase "\\omega_n" \\
         --scope formulas \\
         --format text

   Аргументы:

     * --db-path   — путь к SQLite-базе;
     * --phrase    — поисковая строка;
     * --scope     — 'segments' (чанки блоков, по умолчанию)
                     или 'formulas' (поиск по дереву формул);
     * --category  — опциональный фильтр по подстроке категории;
     * --tag       — опциональный фильтр по подстроке id (например '7d-64');
     * --format    — 'text' или 'json'.

   Поведение:

     * Если есть FTS-таблицы (segments_fts/formulas_fts):
         - используется `MATCH` по соответствующей FTS-таблице
           (фраза автоматически экранируется кавычками);
     * если FTS недоступен — используется обычный LIKE по тексту.

   Результат (text):

     * scope = segments:
         [id] category :: summary
         snippet...
         ----

     * scope = formulas:
         [id] category :: формульная_строка

   Результат (json):

     * список словарей с полями
         - для segments: id, category, summary, snippet
         - для formulas: id, category, formula

Совместимость с остальными режимами
-----------------------------------
Классические режимы search / assemble / stats / validate / tree
работают как и раньше и никак не зависят от наличия SQLite-базы.

Для работы sqlite_build обязательно нужны:
  * --index ALL_index.yaml
  * --theory All.md

Для sqlite_search:
  * --index ALL_index.yaml (для пресетов/совместимости, но внутрь SQLite не лезет);
  * --db-path (готовая база);
  * --phrase.

