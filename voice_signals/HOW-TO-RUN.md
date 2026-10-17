# Voice Signals — Инструкции по запуску (Iteration 02)

## Быстрая проверка работоспособности

### 1. Запуск тестов
```powershell
cd C:\maga\voice_signals
.\.venv\Scripts\python.exe -m pytest -q
```
**Ожидается:** `15 passed in 0.24s`

---

### 2. Запуск VAD на тестовом файле
```powershell
.\.venv\Scripts\python.exe scripts\run_vad.py tests\test_data\Ru-Vegetables.wav
```

**Результат:**
```
File: C:\maga\voice_signals\tests\test_data\Ru-Vegetables.wav
Speech segments: 79
1.290   1.940   speech
2.490   5.480   speech
6.260   7.820   speech
...
```

Сохранённый эталонный результат находится в `tests/result1.md`.

---

### 3. Демонстрационный pipeline (комплексный прогон)
```powershell
.\.venv\Scripts\python.exe scripts\demo_pipeline.py
```

**Что показывает:**
- Config hash и версию
- VAD: число найденных сегментов
- Modified R/S анализ первого сегмента:
  - Показатель Хёрста H
  - Характерное время T
  - Метод fit (piecewise)
  - R-squared
  - Интерпретация (персистентность/антиперсистентность)
- Доступные команды

**Пример вывода:**
```
============================================================
Voice Signals Project - Iteration 02 Demo Pipeline
============================================================

Config hash: e0762e0de9cf4f57
Version: 0.2.0

--------------------Step 1: VAD Analysis--------------------
Detected 79 speech segments:
  1. 1.290 - 1.940s (0.650s)
  2. 2.490 - 5.480s (2.990s)
  ...

-----Step 2: Nonlinear Dynamics Analysis (Modified R/S)-----
Analyzing segment 1 (1.290s - 1.940s)...
  Hurst exponent H: 0.979
  Characteristic time T: 0.250s
  Fit R-squared: 0.995
  Fit method: piecewise
  > Persistent behavior (H > 0.5): long-range correlations detected

--------------------------Summary---------------------------
OK VAD: 79 speech segments detected
OK Modified R/S: H and T computed with piecewise method
```

---

## Полный workflow

### Шаг 1: Генерация синтетических данных
```powershell
.\.venv\Scripts\python.exe scripts\generate_synthetic.py --n-files 10 --seed 42
```

**Результат:**
```
Generating 10 synthetic files...
Config hash: e0762e0de9cf4f57
  syn_000_snr20: 10 events, 6.5s
  syn_001_snr30: 10 events, 6.5s
  ...

OK Generated 10 files with 100 events
OK Manifest: data/synthetic/manifest.csv
OK Metadata: data/synthetic/metadata.json
OK Audio: data/synthetic/audio
OK Labels: data/synthetic/labels
```

**Структура:**
```
data/synthetic/
  audio/
    syn_000_snr20.wav
    syn_001_snr30.wav
    ...
  labels/
    syn_000_snr20.csv  # ground truth
    syn_001_snr30.csv
    ...
  manifest.csv         # сводная таблица
  metadata.json        # config hash, параметры
```

---

### Шаг 2: Аудит WAV-файлов
```powershell
.\.venv\Scripts\python.exe scripts\run_audit.py data\synthetic\audio
```

**Результат:**
```
Found 10 WAV files
  [1/10] syn_000_snr20.wav -> OK
  [2/10] syn_001_snr30.wav -> OK
  ...

OK Audit complete: 10 files
OK Detailed report: reports/wav_audit.csv
OK Summary: reports/wav_audit_summary.md
```

**Отчёты:**
- `reports/wav_audit.csv` — детальный (sample_rate, RMS, peak, clipping, etc.)
- `reports/wav_audit_summary.md` — сводка
- `reports/wav_audit_issues.csv` — только проблемные файлы (если есть)

---

### Шаг 3: Извлечение признаков
```powershell
# Один файл
.\.venv\Scripts\python.exe scripts\extract_features.py tests\test_data\Ru-Vegetables.wav

# Все файлы в директории
.\.venv\Scripts\python.exe scripts\extract_features.py data\synthetic\audio
```

**Результат:**
```
Processing 10 files...
Frame: 25ms, Hop: 10ms
  syn_000_snr20... 260 frames -> syn_000_snr20_features.csv
  syn_001_snr30... 260 frames -> syn_001_snr30_features.csv
  ...

OK Features saved to data/features
```

**Формат CSV:**
```csv
time_sec,rms,energy_db,zcr,spectral_flatness
0.0125,0.042,-27.54,0.12,0.65
0.0225,0.051,-25.83,0.15,0.71
...
```

---

### Шаг 4: Анализ с modified R/S

**Программный API:**
```python
from voice_signals import EnergyVad, modified_rs_hurst
import wave

# VAD
segments = EnergyVad().process_file("data/synthetic/audio/syn_000_snr20.wav")
print(f"Found {len(segments)} segments")

# Load audio
with wave.open("data/synthetic/audio/syn_000_snr20.wav", 'rb') as wf:
    sr = wf.getframerate()
    raw = wf.readframes(wf.getnframes())

audio = [int.from_bytes(raw[i:i+2], 'little', signed=True) / 32768.0 for i in range(0, len(raw), 2)]

# Analyze first segment
if segments:
    seg = segments[0]
    start_idx = int(seg.start_sec * sr)
    end_idx = int(seg.end_sec * sr)
    seg_audio = audio[start_idx:end_idx]
    
    # Новый метод (piecewise fit)
    result = modified_rs_hurst(seg_audio, sr, use_piecewise_fit=True)
    
    if result.valid:
        print(f"Hurst H: {result.hurst_h:.3f}")
        print(f"Characteristic time T: {result.characteristic_time_sec:.3f}s")
        print(f"Fit method: {result.fit_method}")  # "piecewise"
        print(f"R-squared: {result.fit_r_squared:.3f}")
        
        if result.warnings:
            print(f"Warnings: {', '.join(result.warnings)}")
```

---

## Интерпретация показателя Хёрста

| H | Интерпретация |
|---|---------------|
| **H ≈ 0.5** | Броуновское движение (random walk, нет памяти) |
| **0.5 < H < 1.0** | **Персистентный ряд** — тренды сохраняются, долговременные корреляции |
| **0 < H < 0.5** | **Антиперсистентный ряд** — возврат к среднему (mean-reverting) |

Для речи обычно **H > 0.5** (персистентность).

---

## Структура проекта

```
voice_signals/
  src/voice_signals/        # Основной пакет
    vad.py                  # EnergyVad
    vad_backend.py          # Унифицированный интерфейс
    dynamics.py             # Modified R/S (H, T)
    framing.py              # TimeGrid, RMS
    schemas.py              # SegmentRecord, FileAuditRecord, ...
    config.py               # YAML config, hash
  
  scripts/                  # Исполняемые скрипты
    run_vad.py              # VAD на одном файле
    generate_synthetic.py   # Генератор синтетики
    run_audit.py            # Аудит WAV
    extract_features.py     # Извлечение признаков
    demo_pipeline.py        # Комплексная демонстрация
  
  tests/                    # Pytest (15 тестов)
  configs/default.yaml      # Параметры
  docs/                     # Документация
    usage-guide.md          # Полное руководство
    report-iteration-01.md
    report-iteration-02.md
    ITERATION-02-SUMMARY.md # Эта инструкция
  
  data/                     # Данные (не в VCS)
  reports/                  # Отчёты аудита
```

---

## Что изменилось в Iteration 02

### Добавлено:
- ✅ Генератор синтетического корпуса (speech, silence, hesitation, artifact)
- ✅ Аудит WAV (метаданные, энергетика, quality flags)
- ✅ Feature extractor (RMS, ZCR, spectral flatness)
- ✅ Унифицированный интерфейс `VadBackend`
- ✅ Piecewise linear fit для характерного времени T (вместо argmax)

### Изменено:
- `modified_rs_hurst()` — параметр `use_piecewise_fit=True` (по умолчанию)
- `HurstRSResult` — поле `fit_method: str`
- `EnergyVad` наследуется от `VadBackend`
- Config версия: 0.2.0

---

## FAQ

**Q: Какой формат аудио поддерживается?**  
A: Только mono 16-bit PCM WAV.

**Q: Как проверить, что всё работает?**  
A: Запустить `pytest -q` (должно быть 15 passed).

**Q: Где эталонный результат первой итерации?**  
A: В файле `tests/result1.md` (79 сегментов).

**Q: Как изменить порог VAD?**  
A: Создать свой `EnergyVadConfig`:
```python
from voice_signals import EnergyVad, EnergyVadConfig

config = EnergyVadConfig(speech_threshold_db=15.0)
vad = EnergyVad(config)
```

**Q: Что означает fit_method "piecewise"?**  
A: Новый метод расчёта характерного времени T через поиск breakpoint в log(R/S) ~ log(tau). Более точен, чем старый argmax.

**Q: Можно ли использовать старый метод?**  
A: Да, `modified_rs_hurst(audio, sr, use_piecewise_fit=False)`.

---

## Документация

Полные инструкции в `docs/usage-guide.md`.  
Отчёт по итерации в `docs/report-iteration-02.md`.

---

**Версия:** 0.2.0  
**Дата:** 2026-10-17  
**Статус:** Iteration 02 завершена, все тесты проходят
