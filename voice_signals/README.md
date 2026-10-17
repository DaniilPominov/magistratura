# Voice Signals — VAD и анализ нелинейной динамики речи

Локальный Python-пакет для детекции речевой активности (VAD) и анализа временной динамики речевых сигналов через modified R/S-анализ и показатель Хёрста.

**Статус:** Iteration 02 завершена  
**Версия:** 0.2.0  
**Дата:** 2026-10-17

---

## Быстрый старт

### 1. Запуск тестов
```powershell
.\.venv\Scripts\python.exe -m pytest -q
# Ожидается: 15 passed
```

### 2. VAD на файле
```powershell
.\.venv\Scripts\python.exe scripts\run_vad.py tests\test_data\Ru-Vegetables.wav
```

### 3. Демонстрационный pipeline
```powershell
.\.venv\Scripts\python.exe scripts\demo_pipeline.py
```

---

## Основные возможности

- ✅ **Energy VAD** с гистерезисом (детерминированный, без внешних зависимостей)
- ✅ **Modified R/S-анализ** с расчётом показателя Хёрста (H) и характерного времени (T)
- ✅ **Piecewise linear fit** для точной оценки T (реализация методики Кузенкова/Логинова, 2014)
- ✅ **Генератор синтетического корпуса** с ground truth для валидации
- ✅ **Аудит WAV-файлов** (метаданные, энергетика, флаги качества)
- ✅ **Feature extractor** (RMS, ZCR, spectral flatness)
- ✅ **Унифицированный интерфейс** `VadBackend` для будущих адаптеров (WebRTC, Silero)

---

## Использование

### Программный API

```python
from voice_signals import EnergyVad, modified_rs_hurst
import wave

# VAD: детекция речевых сегментов
vad = EnergyVad()
segments = vad.process_file("audio.wav")

for seg in segments:
    print(f"{seg.start_sec:.2f} - {seg.end_sec:.2f} {seg.label}")

# Modified R/S: показатель Хёрста и характерное время
with wave.open("audio.wav", 'rb') as wf:
    sample_rate = wf.getframerate()
    raw = wf.readframes(wf.getnframes())

audio = [
    int.from_bytes(raw[i:i+2], 'little', signed=True) / 32768.0
    for i in range(0, len(raw), 2)
]

result = modified_rs_hurst(audio, sample_rate, use_piecewise_fit=True)

if result.valid:
    print(f"Hurst H: {result.hurst_h:.3f}")
    print(f"Characteristic time T: {result.characteristic_time_sec:.3f}s")
    print(f"Fit method: {result.fit_method}")  # "piecewise"
    print(f"R²: {result.fit_r_squared:.3f}")
```

### Интерпретация показателя Хёрста

- **H ≈ 0.5** — броуновское движение (случайное блуждание)
- **0.5 < H < 1.0** — персистентный ряд (долговременные корреляции, тренды сохраняются)
- **0 < H < 0.5** — антиперсистентный ряд (возврат к среднему, mean-reverting)

---

## Скрипты

| Скрипт | Описание |
|--------|----------|
| `run_vad.py <wav>` | Запуск VAD на одном файле |
| `generate_synthetic.py` | Генерация синтетического корпуса с ground truth |
| `run_audit.py <dir>` | Аудит WAV-файлов (метаданные, энергетика, качество) |
| `extract_features.py <wav>` | Извлечение кадровых признаков (RMS, ZCR, spectral flatness) |
| `demo_pipeline.py` | Комплексная демонстрация: VAD + modified R/S + интерпретация |

---

## Документация

- **[Руководство по использованию](docs/usage-guide.md)** — установка, API, примеры, FAQ
- **[Отчёт Iteration 01](docs/report-iteration-01.md)** — методическая основа, первая итерация
- **[Отчёт Iteration 02](docs/report-iteration-02.md)** — что реализовано во второй итерации
- **[Контракты данных](docs/contracts.md)** — спецификация SegmentRecord, FileAuditRecord, etc.

---

## Что реализовано в Iteration 02

- **TASK-09**: Генератор синтетического корпуса с ground truth (speech, silence, hesitation, artifact)
- **TASK-01**: Аудит WAV (sample rate, каналы, RMS, clipping, noise floor, quality flags)
- **TASK-02**: Feature extractor (RMS, energy dB, ZCR, spectral flatness)
- **TASK-06**: Унифицированный интерфейс `VadBackend` для адаптеров
- **TASK-11**: Улучшение modified R/S — piecewise linear fit для характерного времени T (вместо argmax)

---

## Ограничения

- Формат: **только mono 16-bit PCM WAV**
- Нет MFCC, log-Mel, FFT-based признаков (требуют numpy/scipy)
- Нет WebRTC/Silero адаптеров (интерфейс готов, реализации в будущих итерациях)
- Нет реальной gold-разметки и метрик качества (precision/recall/F1)

---

## Структура

```
voice_signals/
  src/voice_signals/        # Основной пакет
    vad.py                  # EnergyVad с гистерезисом
    vad_backend.py          # Унифицированный интерфейс
    dynamics.py             # Modified R/S, Hurst H, время T
    framing.py              # Единая временная сетка и RMS
    schemas.py              # Контракты данных
    config.py               # YAML конфигурация и hash
  
  scripts/                  # Исполняемые скрипты
  tests/                    # Unit-тесты (pytest, 15 passed)
  configs/default.yaml      # Параметры (framing, VAD, dynamics)
  docs/                     # Документация
  data/                     # Данные (не в VCS)
  reports/                  # Отчёты аудита
```

---

## Зависимости

Минимальны: только `pyyaml`.  
Нет numpy, scipy, torch, librosa.

---

## Воспроизводимость

Все алгоритмы детерминированы. Используется **config hash** (SHA256) для трекинга параметров экспериментов.

```python
from voice_signals import load_config, config_hash

config = load_config("configs/default.yaml")
print(config_hash(config))  # a3f7c8d9e2b1...
```

---

## Следующие шаги (Iteration 03)

- Реальная gold-разметка (Label Studio, IAA)
- WebRTC VAD адаптер
- Метрики качества (precision, recall, F1, IoU, latency, false pause precision)
- Subject-level split для валидации
- DFA-Hurst для сравнения с modified R/S
- Lyapunov (exploratory)

---

## Ссылки

- **Методика:** Н. П. Кузенков, В. М. Логинов. «Использование метода нормированного размаха при анализе речевых патологий неврологического генеза», Компьютерные исследования и моделирование, 2014
- **Контракты:** [docs/contracts.md](docs/contracts.md)
- **Отчёты:** [docs/report-iteration-01.md](docs/report-iteration-01.md), [docs/report-iteration-02.md](docs/report-iteration-02.md)

---

**Лицензия:** Для исследовательских целей  
**Контакты:** См. agent/rules/project-agreements.md
