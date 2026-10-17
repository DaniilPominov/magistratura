# Voice Signals — Руководство по запуску (Iteration 02)

Проект `voice_signals` — локальный Python-пакет для сегментации речевой активности (VAD) и анализа нелинейной динамики речевых сигналов.

## Быстрый старт

### Установка зависимостей

```powershell
cd voice_signals
.\.venv\Scripts\python.exe -m pip install -r requirements.txt  # если есть
```

Проект не требует внешних зависимостей, кроме `pyyaml`.

### Запуск тестов

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

Ожидается: **15 passed**.

---

## Основные сценарии использования

### 1. Запуск VAD на одном файле

Детекция речевых сегментов в WAV-файле:

```powershell
.\.venv\Scripts\python.exe scripts\run_vad.py tests\test_data\Ru-Vegetables.wav
```

**Вывод:**
```
File: C:\maga\voice_signals\tests\test_data\Ru-Vegetables.wav
Speech segments: 79
1.290   1.940   speech
2.490   5.480   speech
...
```

Для собственного WAV-файла:

```powershell
.\.venv\Scripts\python.exe scripts\run_vad.py path\to\your\file.wav
```

---

### 2. Генерация синтетического корпуса

Создание синтетических аудио с ground-truth разметкой для валидации:

```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic.py --n-files 10 --seed 42
```

**Параметры:**
- `--output-dir` — директория для результатов (по умолчанию `data/synthetic`)
- `--n-files` — количество файлов (по умолчанию 10)
- `--sample-rate` — частота дискретизации в Гц (по умолчанию 16000)
- `--seed` — random seed для воспроизводимости (по умолчанию 42)

**Результат:**
```
data/synthetic/
  audio/           # WAV-файлы
  labels/          # CSV с ground truth для каждого файла
  manifest.csv     # сводная таблица
  metadata.json    # метаданные корпуса
```

---

### 3. Аудит WAV-файлов

Анализ метаданных, энергетики и качества аудио:

```powershell
.\.venv\Scripts\python.exe scripts\run_audit.py data\synthetic\audio
```

**Параметры:**
- `input_dir` — директория с WAV-файлами
- `--output-dir` — директория для отчётов (по умолчанию `reports`)
- `--recursive` — рекурсивный поиск WAV

**Результат:**
```
reports/
  wav_audit.csv         # детальный отчёт по каждому файлу
  wav_audit_summary.md  # сводка: sample rate, длительность, флаги качества
  wav_audit_issues.csv  # файлы с проблемами (clipping, low energy, etc.)
```

---

### 4. Извлечение признаков

Расчёт кадровых признаков (RMS, ZCR, spectral flatness):

```powershell
# Один файл
.\.venv\Scripts\python.exe scripts\extract_features.py tests\test_data\Ru-Vegetables.wav

# Все файлы в директории
.\.venv\Scripts\python.exe scripts\extract_features.py data\synthetic\audio
```

**Параметры:**
- `--output-dir` — директория для CSV с признаками (по умолчанию `data/features`)
- `--frame-ms` — размер кадра в мс (по умолчанию 25)
- `--hop-ms` — шаг кадра в мс (по умолчанию 10)

**Результат:**
```
data/features/
  file_001_features.csv
  file_002_features.csv
  ...
```

Каждый CSV содержит столбцы: `time_sec`, `rms`, `energy_db`, `zcr`, `spectral_flatness`.

---

### 5. Демонстрационный pipeline (Iteration 02)

Комплексный прогон всех компонентов:

```powershell
.\.venv\Scripts\python.exe scripts\demo_pipeline.py
```

**Что делает:**
1. Загружает конфигурацию и показывает hash
2. Запускает VAD на тестовом файле
3. Анализирует первый речевой сегмент с помощью modified R/S (Hurst H, характерное время T)
4. Показывает интерпретацию (персистентность, антиперсистентность)
5. Выводит доступные команды и next steps

---

## Программный API

### Использование VAD

```python
from voice_signals import EnergyVad

vad = EnergyVad()
segments = vad.process_file("path/to/audio.wav")

for seg in segments:
    print(f"{seg.start_sec:.2f} - {seg.end_sec:.2f} {seg.label}")
```

### Анализ нелинейной динамики

```python
from voice_signals import modified_rs_hurst
import wave

# Загрузить аудио
with wave.open("path/to/audio.wav", 'rb') as wf:
    sample_rate = wf.getframerate()
    raw = wf.readframes(wf.getnframes())

audio = [
    int.from_bytes(raw[i:i+2], 'little', signed=True) / 32768.0
    for i in range(0, len(raw), 2)
]

# Расчёт показателя Хёрста и характерного времени
result = modified_rs_hurst(audio, sample_rate, use_piecewise_fit=True)

if result.valid:
    print(f"Hurst H: {result.hurst_h:.3f}")
    print(f"Characteristic time T: {result.characteristic_time_sec:.3f}s")
    print(f"Fit method: {result.fit_method}")  # "argmax" or "piecewise"
    print(f"R²: {result.fit_r_squared:.3f}")
else:
    print(f"Invalid result: {result.warnings}")
```

**Интерпретация H:**
- `H ≈ 0.5` — броуновское движение (случайное блуждание)
- `0.5 < H < 1.0` — персистентный ряд (долговременные корреляции)
- `0 < H < 0.5` — антиперсистентный ряд (возврат к среднему)

---

## Структура проекта

```
voice_signals/
  src/voice_signals/        # Основной пакет
    __init__.py             # Публичный API (38 экспортов)
    schemas.py              # Контракты данных (SegmentRecord, FileAuditRecord, ...)
    framing.py              # Единая временная сетка и RMS-огибающая
    vad.py                  # EnergyVad с гистерезисом
    vad_backend.py          # Унифицированный интерфейс VadBackend
    dynamics.py             # Modified R/S-анализ, Hurst H, время T
    config.py               # Загрузка YAML, hash, валидация
  
  configs/default.yaml      # Параметры (framing, VAD, dynamics, taxonomy)
  
  scripts/                  # Исполняемые скрипты
    run_vad.py              # VAD на одном файле
    generate_synthetic.py   # Генерация синтетического корпуса
    run_audit.py            # Аудит WAV-файлов
    extract_features.py     # Извлечение кадровых признаков
    demo_pipeline.py        # Комплексная демонстрация
  
  tests/                    # Unit-тесты (pytest)
    test_vad.py             # Тесты VAD и dynamics
    test_framing.py         # Тесты фрейминга
    test_config.py          # Тесты конфигурации
    test_data/              # Тестовые WAV-файлы
  
  data/                     # Данные (не в VCS)
    synthetic/              # Синтетический корпус
    raw/                    # Исходные реальные данные
    features/               # Извлечённые признаки
    segments/               # Результаты VAD
  
  reports/                  # Отчёты аудита и метрик
  
  docs/                     # Документация
    report-iteration-01.md  # Отчёт первой итерации
    report-iteration-02.md  # Отчёт второй итерации
    contracts.md            # Спецификация контрактов
    usage-guide.md          # Это руководство
```

---

## Конфигурация

Параметры задаются в `configs/default.yaml`:

```yaml
framing:
  sample_rate: 16000  # Частота дискретизации (Гц)
  frame_ms: 20.0      # Размер кадра (мс)
  hop_ms: 10.0        # Шаг кадра (мс)

vad:
  energy:
    speech_threshold_db: 10.0    # Порог входа в речь (дБ)
    release_threshold_db: 6.0    # Порог удержания речи (дБ)
    noise_percentile: 0.2        # Перцентиль для оценки шума
    min_speech_ms: 80.0          # Минимальная длительность речи (мс)
    min_pause_ms: 80.0           # Минимальная пауза между сегментами (мс)

dynamics:
  modified_rs:
    envelope_window_sec: 0.025   # Окно огибающей для R/S (с)
    min_tau: 4                   # Минимальный tau
    max_tau: null                # Максимальный tau (auto: len(envelope) // 2)
    r_squared_threshold: 0.7     # Минимальный R² для валидности

taxonomy:
  labels: ["speech", "silent_pause", "hesitation", "artifact"]
  mvp_binary: ["speech", "non_speech"]
```

Для воспроизводимости экспериментов используется **config hash** — стабильный SHA256 конфигурации.

---

## Изменения в Iteration 02

По сравнению с первой итерацией:

### Добавлено:
- ✅ **TASK-09**: Генератор синтетического корпуса с ground truth (`generate_synthetic.py`)
- ✅ **TASK-01**: Аудит WAV-файлов (`run_audit.py`)
- ✅ **TASK-02**: Feature extractor (RMS, ZCR, spectral flatness) (`extract_features.py`)
- ✅ **TASK-06**: Унифицированный интерфейс `VadBackend` для будущих WebRTC/Silero адаптеров
- ✅ **TASK-11**: Улучшен modified R/S — добавлен piecewise linear fit для расчёта характерного времени T (вместо argmax)

### Изменено:
- `modified_rs_hurst()` теперь возвращает `fit_method` (`"argmax"` или `"piecewise"`)
- Параметр `use_piecewise_fit=True` (по умолчанию) включает более точную оценку T
- `EnergyVad` теперь наследуется от `VadBackend`

### Известные ограничения:
- Формат: только mono 16-bit PCM WAV
- Нет MFCC/Mel-спектрограмм (требуют дополнительных зависимостей)
- Нет WebRTC/Silero адаптеров (интерфейс готов, реализации в будущих итерациях)
- Нет реальной gold-разметки и метрик качества (precision/recall/F1)

---

## FAQ

**Q: Какой формат аудио поддерживается?**  
A: Только mono 16-bit PCM WAV. Stereo, другие битности и форматы (MP3, OGG) не поддерживаются.

**Q: Как изменить порог VAD?**  
A: Создайте свой YAML конфиг или передайте `EnergyVadConfig` программно:
```python
from voice_signals import EnergyVad, EnergyVadConfig

config = EnergyVadConfig(speech_threshold_db=15.0, release_threshold_db=8.0)
vad = EnergyVad(config)
```

**Q: Что означает Hurst exponent H?**  
A: Показатель Хёрста характеризует самоподобие временного ряда. H > 0.5 указывает на персистентное поведение (тренды сохраняются), H < 0.5 — на антиперсистентное (возврат к среднему), H ≈ 0.5 — на случайное блуждание.

**Q: Зачем нужен config hash?**  
A: Для воспроизводимости экспериментов. Каждый эксперимент сохраняет config hash, чтобы можно было точно восстановить параметры.

**Q: Можно ли использовать VAD в real-time?**  
A: Текущая реализация работает с готовыми файлами. Real-time требует streaming интерфейса (будет в следующих итерациях).

---

## Ссылки

- [Отчёт Iteration 01](docs/report-iteration-01.md) — методическая основа, первая итерация
- [Отчёт Iteration 02](docs/report-iteration-02.md) — что реализовано во второй итерации
- [Контракты данных](docs/contracts.md) — спецификация SegmentRecord, FileAuditRecord, etc.
- [Kuzenkov & Loginov (2014)](docs/kuzenkov/crm358.md) — источник методики modified R/S

---

**Версия:** 0.2.0  
**Дата:** 2026-10-17  
**Статус:** Iteration 02 завершена
