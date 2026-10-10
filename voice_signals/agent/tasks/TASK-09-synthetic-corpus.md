# TASK-09. Синтетический корпус и end-to-end тесты

Роль: Test infrastructure agent. Файлы результата: `synthetic_corpus_generator.py`, `end_to_end_synthetic_test.py`, `metrics_segment.py`. Контракты данных находятся в TASK-00.

## Цель
Воспроизводимый синтетический корпус для проверки всего пайплайна до получения реальных данных. Минимальная версия нужна уже в волне 1 (для TASK-01 и TASK-02), затем корпус расширяется.

## Вход
Конфиг: sample_rate, duration_range, параметры speech-like, pause, hesitation, breath, artifact, noise_levels, codec_simulation (опционально).

```yaml
synthetic:
  sample_rate: 16000
  files: 50
  duration_sec: [30, 120]
  speech_rate_hz: [2, 6]
  pause_prob: 0.3
  hesitation_prob: 0.1
  artifact_prob: 0.05
  snr_db: [5, 10, 20, 30]
```

## Выход
```text
data/synthetic/
  audio/
  labels/
  manifest.csv
  README.md
```
Плюс скрипт генерации, интеграционные тесты, config hash.

## События
- Speech-like: гармоническая структура, формантоподобные пики, вариативная энергия, слоги и слова, паузы между словами. Для MVP достаточно гармонических burst-ов.
- Silent pause: низкая энергия, без voiced, 100–2000 мс, иногда фоновый шум.
- Hesitation-like: voiced, низкая информационная плотность, устойчивый тон, 60–800 мс, энергия ниже speech. Аппроксимация гармоническим сигналом с медленной модуляцией.
- Breath-like artifact: шумоподобный спектр, высокий ZCR, низкая гармоничность, плавный или резкий onset/offset.
- Transient artifact: клик, удар, щелчок, короткий широкополосный всплеск, клиппинг.
- Шум: белый, розовый, офисный гул; SNR 5, 10, 20, 30 dB. Опционально реверберация, сжатие, ресемплинг.

## Ground truth
На каждый файл: start_sec, end_sec, label, event_type, generation_parameters. Скрытые параметры: true_H, true_entropy, noise_level, speaker_like_pitch. Они позволяют проверять и VAD, и динамические признаки.

## Шаги
1. Конфиг генератора (YAML).
2. Функции: generate_speech_like_segment, generate_silent_pause, generate_hesitation_like_segment, generate_breath_like_artifact, generate_transient_artifact.
3. Сборка timeline: без непреднамеренных пересечений, сохранение ground truth, воспроизводимость по seed.
4. Смешивание с шумом по заданному SNR.
5. Экспорт: WAV, labels CSV, manifest, config hash.
6. MVP E2E: audit -> features -> VAD adapters -> pseudo-labels -> metrics. Динамические модули проверяются отдельным расширенным прогоном после их готовности.
7. Деградационные тесты: низкий SNR, клиппинг, разная длительность, пустой файл, очень короткий файл, резкое изменение громкости.

## Критерии приёмки
1. Не менее 50 файлов за приемлемое время.
2. Ground truth соответствует аудио.
3. MVP-контур выполняется на синтетике; расширенный прогон динамических модулей является отдельным критерием.
4. Метрики считаются без ошибок.
5. Pseudo-label generator даёт измеримое качество на известных метках.
6. Тесты падают при намеренной порче контрактов, например при переходе секунд в кадры без конвертации.

## Тесты
- Структурные: сумма длительностей сегментов не превышает длительность файла; нет пересечений (если не моделируется overlap); все label из таксономии; времена неотрицательны.
- Акустические: speech-like более гармоничен, чем breath; silent pause низкоэнергетичен; transient короткий с высоким ZCR; hesitation отличается от speech по сложности и энергии.
- Pipeline тест в CI или локально.

## Ошибки, которых избегать
- Синтетическая речь, подогнанная под тот же алгоритм, который тестируется.
- Не сохранённая ground truth.
- Нереалистичные длительности.
- Отсутствие шума и артефактов.
- Вывод о реальных данных на основании только синтетики.

## Инструкция агенту
Реализуй генератор синтетического речевого корпуса с ground truth: speech-like, silent_pause, hesitation-like, breath-like и transient artifact. Конфигурируемые sample rate, SNR, длительность, seed. Минимальная версия нужна для ранних тестов, полная — не менее 50 файлов и manifest. Добавь MVP E2E-тест на audit -> features -> VAD -> pseudo-labels -> metrics; расширенный тест динамических модулей добавь после TASK-03--TASK-05. Корпус должен позволять измерять false pause rate и hesitation recall.
