ЗАДАЧА: подготовить полноценный датасет для сопоставления атомных переходов и сверхновых как переходных событий.

ЦЕЛЬ
Получить два чистых и пригодных для дальнейшего анализа набора данных:
1. атомные переходы
2. сверхновые как транзиентные события

И дополнительно:
3. объединённый датасет событийных признаков для последующей кластеризации и корреляционного анализа.

ИСТОЧНИКИ ДАННЫХ

1) Атомные переходы
Источник: NIST Atomic Spectra Database
Нужно получить реальные таблицы переходов, а не HTML-ошибки и не пустые CSV.

Обязательные поля:
- element
- ion_stage
- lower_level
- upper_level
- wavelength_nm
- frequency_Hz
- energy_eV
- Aki
- lifetime_s
- J_lower
- J_upper
- parity_lower
- parity_upper

Если lifetime_s отсутствует напрямую:
- вычислить lifetime_s = 1 / Aki при Aki > 0

Если frequency_Hz отсутствует:
- вычислить по wavelength

2) Сверхновые
Источники:
- Open Supernova Catalog
- при необходимости TNS / другие открытые каталоги light curves

Обязательные поля:
- name
- type
- redshift
- distance_Mpc
- peak_mag
- peak_abs_mag
- peak_luminosity_proxy
- rise_time_days
- decay_time_days
- width_days
- number_of_points
- band
- has_lightcurve

Если есть light curve:
- сохранить полную временную серию в отдельной таблице

ОЧИСТКА ДАННЫХ

Атомные переходы:
- убрать строки без wavelength и без Aki
- убрать нефизические значения
- привести единицы к единому виду

Сверхновые:
- убрать события без peak_abs_mag
- отдельно выделить поднабор с валидными rise/decay/width
- не генерировать синтетику
- не заполнять пропуски выдуманными значениями

ВЫЧИСЛЯЕМЫЕ ПОЛЯ

Для атомных переходов вычислить:
- deltaE_eV
- tau_s
- nu_Hz
- Q_proxy = nu_Hz * tau_s
- deltaJ = J_upper - J_lower
- parity_change = indicator(parity_upper != parity_lower)

Для сверхновых вычислить:
- L_proxy = 10^(-0.4 * peak_abs_mag)
- t0_days = (rise_time_days + decay_time_days)/2, только если оба есть
- asymmetry = decay_time_days / rise_time_days, только если оба есть и rise_time_days > 0
- width_norm = width_days / t0_days, только если оба есть
- event_strength = L_proxy * t0_days, только если t0_days есть

ПОДГОТОВИТЬ ТРИ ИТОГОВЫЕ ТАБЛИЦЫ

1. atomic_transition_events.csv
Колонки:
- transition_id
- element
- ion_stage
- deltaE_eV
- tau_s
- nu_Hz
- Q_proxy
- deltaJ
- parity_change
- wavelength_nm
- Aki

2. supernova_transient_events.csv
Колонки:
- event_id
- name
- type
- redshift
- distance_Mpc
- peak_abs_mag
- L_proxy
- rise_time_days
- decay_time_days
- width_days
- t0_days
- asymmetry
- width_norm
- event_strength
- has_lightcurve
- number_of_points

3. cluster_ready_events.csv
Объединённая таблица только с валидными строками.
Колонки:
- event_id
- domain   (atomic / supernova)
- logE
- logt
- logQ_or_width
- shape_1
- shape_2
- class_hint

Где:
для atomic:
- logE = log10(deltaE_eV)
- logt = log10(tau_s)
- logQ_or_width = log10(Q_proxy)
- shape_1 = deltaJ
- shape_2 = parity_change

для supernova:
- logE = log10(L_proxy)
- logt = log10(t0_days)
- logQ_or_width = log10(width_norm) или log10(width_days), если width_norm недоступен
- shape_1 = asymmetry
- shape_2 = number_of_points

ДОПОЛНИТЕЛЬНО

Сделать отчёт:
- сколько строк было загружено
- сколько отброшено
- сколько осталось
- по каким причинам строки отбрасывались
- какие поля реально есть, а какие отсутствуют

СОХРАНИТЬ В АРХИВ

Структура архива:
- /data
  - atomic_transition_events.csv
  - supernova_transient_events.csv
  - cluster_ready_events.csv
  - supernova_lightcurves_long.csv   (если удалось)
- /scripts
  - download_atomic.py
  - download_supernova.py
  - clean_atomic.py
  - clean_supernova.py
  - build_cluster_ready.py
- /report
  - data_report.md
  - missingness_report.csv
  - source_manifest.csv
- README.md

КРИТИЧЕСКИ ВАЖНО
- никаких синтетических данных
- никаких вымышленных значений
- если поле отсутствует, оставить пустым
- все источники должны быть реальными
- все скрипты должны быть воспроизводимыми

ADDITIONAL SPECIFICATIONS

1. parity
If not provided by source:
parity = 1 if term contains (o, °, odd)
parity = 0 otherwise

2. energy units
All energies must be converted to eV.

Conversion:
E_eV = E_cm-1 / 8065.54429

Transition energy:
deltaE_eV = (Ek - Ei) / 8065.54429

3. IDs
transition_id:
{element}_{ion}_{lower}_{upper}_{row}

event_id:
use supernova name, append index if duplicates

4. class_hint
atomic → atomic_transition
supernova → stellar_transient

5. script names
Do not rename existing scripts.
Provide wrapper scripts matching spec names.

6. light curves
Light curve is considered valid only if
number_of_points ≥ 20.