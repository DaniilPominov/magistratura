# TASK-04. Sample entropy и permutation entropy

Роль: Complexity metrics agent. Файл результата: `entropy.py`.

## Цель
Меры сложности и регулярности временных рядов. Могут быть устойчивее прямой оценки Ляпунова; полезны для VAD и когнитивного анализа.

## Вход
Одномерный ряд: energy envelope, log-energy, spectral flux, pitch contour, MFCC-компонента. Параметры: m, r, window_sec, hop_sec, normalize, delay.

## Выход
По окнам: sample_entropy, permutation_entropy, validity_flag, n_points, parameters_hash.
Агрегаты: mean, median, std, p10, p90, valid_ratio.
Каждый признак хранит: algorithm, m, r, delay, normalize, window_sec, hop_sec, version.

## Алгоритмы
- Sample entropy: SampEn(m, r, N) = -ln(B^{m+1} / A^m), где A^m и B^{m+1} — число совпадений длины m и m+1 при допуске r. Начально: m = 2, r = 0.1–0.2 std, ряд нормализован.
- Permutation entropy: распределение порядковых паттернов длины m (m = 3 или 4, delay = 1), энтропия Шеннона, нормировка на log(m!).

## Шаги
1. `windowed_entropy(series, window_sec, hop_sec, samplerate)`.
2. `sample_entropy(series, m, r)`.
3. `permutation_entropy(series, m, delay, normalize)`.
4. Валидность: слишком короткий ряд, нулевая дисперсия, NaN, избыток повторов.
5. Сохранение параметров в метаданных.

## Критерии приёмки
1. Периодический сигнал: низкая permutation entropy.
2. Белый шум: высокая entropy.
3. Постоянный сигнал: вырожденный флаг или явно минимальная энтропия с флагом.
4. Воспроизводимость.
5. Параметры в метаданных.

## Тесты
- Синус, белый шум, розовый шум, логистическое отображение (хаос), постоянный сигнал, сильный тренд.
- Benchmark: permutation entropy дешевле sample entropy на длинных рядах (без преждевременной оптимизации).

## Ошибки, которых избегать
- Sample entropy на очень коротких окнах без флагов.
- Отсутствие нормализации ряда.
- Смешивание абсолютной и нормированной энтропии.
- Трактовка энтропии как прямой меры когнитивной нагрузки без контроля confounders.

## Инструкция агенту
Реализуй sample entropy и permutation entropy для одномерных рядов с оконным wrapper. Параметры m, r, delay, normalize. Флаги валидности для коротких и вырожденных рядов. Параметры в метаданных. Тесты на синусе, белом шуме, хаотическом ряде и постоянном сигнале.
