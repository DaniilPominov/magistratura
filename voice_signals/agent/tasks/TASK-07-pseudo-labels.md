# TASK-07. Генератор pseudo-labels

Роль: Pseudo-labeling agent. Файл результата: `pseudo_label_generator.py`.

## Цель
Черновая многоклассовая разметка для ускорения ручной коррекции и первичного обучения. Pseudo-labels не являются ground truth.

## Вход
- Аудио.
- Кадровые признаки TASK-02.
- Динамические признаки TASK-03–05, если доступны.
- Сегменты VAD TASK-06 (Silero, WebRTC, energy).

## Выход
`pseudo_labels/{file_id}.csv` или `.json`. Поля: file_id, subject_id, task_type, start_sec, end_sec, label, confidence, source_rules, disagreement_score, review_required.

Метки: `speech`, `silent_pause`, `hesitation`, `artifact`.

## Логика
1. Speech: strong_speech = Silero AND WebRTC; weak_speech = один backend.
2. Silent pause: non-speech по VAD, низкая энергия, низкая voicing, нет транзиентов, длительность >= min_silent_pause_ms. Дыхание и шум не должны автоматически становиться паузой.
3. Hesitation: voiced или harmonic, энергия ниже медианы speech, низкая спектральная сложность, устойчивый низкочастотный компонент, длительность 60–800 мс, не сильный speech. Без транскрипции низкая уверенность и review_required=true.
4. Artifact: высокий ZCR, транзиентная энергия, низкая гармоничность, очень короткая длительность, резкий onset/offset, дыхание, клиппинг. Дыхание в MVP — artifact.

## Шаги
1. Кадровая классификация: P_speech_candidate, P_silence_candidate, P_hesitation_candidate, P_artifact_candidate на основе VAD agreement, energy, ZCR, spectral flatness, voicing, SNR, Hurst/entropy.
2. Сегментация: гистерезис, минимальные длительности, merge однородных, split при смене класса.
3. Конфликты, консервативно: artifact -> hesitation (voiced low-information) -> speech (strong) -> silent_pause (длинно и тихо) -> иначе artifact или unknown (внутренний статус).
4. Confidence 0.0–1.0 по agreement VAD, расстоянию до границы решения, SNR, artifact likelihood, стабильности признаков.
5. review_required: короткие сегменты, низкая уверенность, disagreement Silero/WebRTC, hesitation, artifact рядом со speech, низкий SNR.
6. Экспорт: внутренний CSV, Label Studio JSON, Praat TextGrid.

## Критерии приёмки
1. Сегменты внутри файла не пересекаются.
2. Каждый сегмент имеет label, confidence, source_rules.
3. На синтетике с известной ground truth считаются pseudo_speech_precision, pseudo_silence_precision, pseudo_hesitation_recall, false_pause_rate.
4. Ни один pseudo-label не помечен как gold.
5. Прогон всего синтетического корпуса за приемлемое время.
6. Загрузка в Label Studio работает.

## Тесты
- Чередование speech и silence.
- Вставка hesitation-like гармонических низкоэнергетических сегментов.
- Вставка breath-like шума и click-артефактов.
- Белый шум и клиппинг.
- Метрики: speech precision > 0.85, silent pause precision > 0.70, hesitation recall > 0.40, false pause rate < 0.20. Пороги калибруются, но измеримость обязательна.

## Ошибки, которых избегать
- Считать всю non-speech тишиной.
- Не помечать спорные hesitation для проверки.
- Использовать pseudo-labels как ground truth.
- Пересекающиеся сегменты.
- Потеря provenance (какой backend и какое правило породили метку).

## Инструкция агенту
Реализуй генератор pseudo-labels для четырёх классов. Используй кадровые признаки, VAD-выходы и эвристики для voiced low-information событий. Непересекающиеся сегменты с confidence, source_rules и review_required. Экспорт в CSV, Label Studio JSON и Praat TextGrid. Оцени false pause rate на синтетическом корпусе с известной разметкой.
