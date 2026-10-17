# Changelog

Все значимые изменения в проекте voice_signals документируются здесь.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/).

---

## [0.2.0] - 2026-10-17

### Добавлено

- **TASK-09**: Генератор синтетического корпуса с ground truth
  - 4 типа событий: speech, silent_pause, hesitation, artifact
  - Контролируемый SNR (5/10/20/30 дБ)
  - Ground truth с `start_sec`, `end_sec`, `label`, `true_h`, `noise_level_db`
  - Экспорт: WAV + CSV разметка + manifest + metadata.json

- **TASK-01**: Аудит WAV-файлов (базовая версия)
  - Метаданные: sample rate, каналы, длительность, битность
  - Энергетика: RMS, peak, crest factor, noise floor
  - Флаги качества: clipping, low_energy, mostly_silent, unusual_sample_rate
  - Три отчёта: детальный, сводка, issues-only

- **TASK-02**: Feature extractor (базовая версия)
  - RMS, energy (dB), zero-crossing rate, spectral flatness (упрощённая)
  - Без numpy/scipy – чистый Python
  - CSV-экспорт с таймкодами

- **TASK-06**: Унифицированный интерфейс `VadBackend`
  - Базовый класс для всех VAD-адаптеров
  - `EnergyVad` теперь наследуется от `VadBackend`
  - Готов к добавлению WebRTC/Silero

- **TASK-11**: Улучшение modified R/S
  - **Piecewise linear fit для характерного времени T** (вместо argmax)
  - Новое поле `fit_method` в `HurstRSResult`: `"argmax"` или `"piecewise"`
  - Параметр `use_piecewise_fit` в `modified_rs_hurst()` (по умолчанию `True`)
  - Обратная совместимость сохранена

- **Документация**:
  - `docs/usage-guide.md` – детальное руководство
  - `docs/report-iteration-02.md` – отчёт о второй итерации
  - `docs/project-status-2026-10-17.md` – оценка состояния проекта
  - `docs/questions-for-advisor.md` – вопросы к научному руководителю
  - `docs/README.md` – навигация по документации
  - `NEXT_STEPS.md` – следующие шаги
  - Литературная база расширена (4 новых источника)

- **Скрипты**:
  - `scripts/generate_synthetic.py` – генератор синтетического корпуса
  - `scripts/run_audit.py` – аудит WAV-файлов
  - `scripts/extract_features.py` – извлечение кадровых признаков
  - `scripts/demo_pipeline.py` – демонстрационный pipeline

### Изменено

- `modified_rs_hurst()` теперь использует piecewise fit по умолчанию
- `HurstRSResult` содержит `fit_method` для различения методов оценки T
- `README.md` обновлён с указанием критического блокера

### Исправлено

- Характерное время T теперь оценивается более точно (piecewise fit вместо argmax)
- Улучшена методическая точность (ближе к статье Кузенкова/Логинова, 2014)

---

## [0.1.0] - 2026-10-12

### Добавлено

- **Первый релиз (Iteration 01)**
- Energy VAD с гистерезисом
  - Двухпороговая детекция (вход 10 дБ, выход 6 дБ)
  - Постобработка: минимальная речь/пауза 80 мс
  - Детерминированный, без внешних ML-зависимостей
  - Выдаёт непересекающиеся `SegmentRecord`

- Modified R/S-анализ (обязательная нелинейная ветвь)
  - Методика Кузенкова/Логинова (2014)
  - Показатель Хёрста `H` через log-log регрессию
  - Характерное время `T` (через argmax R/S)
  - Флаги валидности и предупреждения

- Единые контракты данных
  - `SegmentRecord` – сегмент речевой активности
  - `FileAuditRecord` – результат аудита WAV
  - `FrameFeatureRecord` – кадровые признаки
  - `ExperimentRecord` – запись эксперимента

- Единый слой фрейминга
  - `TimeGrid` – временная сетка
  - `compute_rms_frames` – RMS-огибающая
  - `FrameScore` – покадровый результат VAD

- Конфигурационный слой
  - YAML конфигурация (`configs/default.yaml`)
  - Config hash (SHA256) для воспроизводимости
  - Валидация конфигурации

- Тесты
  - 15 детерминированных unit-тестов (pytest)
  - Синтетические сигналы для проверки

- Документация
  - `README.md` – краткая сводка
  - `docs/report-iteration-01.md` – отчёт о первой итерации
  - `docs/contracts.md` – спецификация контрактов
  - `docs/kuzenkov/crm358.md` – выжимка методики

- Скрипты
  - `scripts/run_vad.py` – запуск VAD на WAV-файле

### Ограничения

- Формат аудио: только mono 16-bit PCM WAV
- Нет ресемплинга, stereo downmix, других форматов
- Нет gold-разметки реальных данных
- Нет метрик качества (precision, recall, F1)
- Нет WebRTC/Silero адаптеров
- Характерное время T оценивается грубо (argmax)

---

## Легенда

- **Добавлено** – новая функциональность
- **Изменено** – изменения в существующей функциональности
- **Устарело** – функциональность, которая скоро будет удалена
- **Удалено** – удалённая функциональность
- **Исправлено** – исправления багов
- **Безопасность** – исправления уязвимостей

---

## Планы на [0.3.0] (Iteration 03)

### Критические блокеры

- 🔴 Получить реальный корпус
- 🔴 Gold-разметка (Label Studio, IAA ≥ 0.8)
- 🔴 WebRTC VAD адаптер
- 🔴 Subject-level split

### Дополнительные улучшения

- Метрики качества (precision, recall, F1, IoU, false_pause_precision)
- DFA-Hurst для сравнения с modified R/S
- Спектральные признаки (MFCC, log-Mel)
- Собственный VAD с H/T (абляции, сравнение с baseline)
- MVP-gate

**Детали:** См. [NEXT_STEPS.md](NEXT_STEPS.md) и [docs/project-status-2026-10-17.md](docs/project-status-2026-10-17.md)
