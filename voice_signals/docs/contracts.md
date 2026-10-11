# Контракты данных voice_signals

Все модули используют единые структуры обмена.

## Единицы измерения
- **Время**: секунды с плавающей точкой
- **Частота**: Гц (целое число)
- **Энергия**: дБ относительно baseline

## Таксономия MVP
- `speech`: речевые сегменты
- `silent_pause`: тишина
- `hesitation`: гезитации
- `artifact`: дыхание, артефакты

Бинарная упрощённая версия (итерация 01): `speech` / `non_speech`.

## Контракты

### `SegmentRecord`
Сегмент речевой активности. Используется всеми VAD-модулями.

**Поля**:
- `file_id: str` — идентификатор файла
- `subject_id: str | None` — респондент (может быть `None` или `"UNKNOWN"`)
- `task_type: str` — тип задачи (`"vad"`, `"reading"`, `"monologue"`)
- `start_sec: float` — начало сегмента (секунды)
- `end_sec: float` — конец сегмента (секунды)
- `label: str` — метка из таксономии
- `score: float | None` — уверенность [0, 1]
- `source_backend: str` — источник (`"energy"`, `"webrtc"`, `"custom_vad"`)
- `is_pseudo_label: bool` — флаг pseudo-label (не gold-разметка)
- `notes: str` — доп. информация

**Инварианты**:
- `0 <= start_sec < end_sec`
- `label in LABELS`
- `score is None or 0 <= score <= 1`

**Проверка пересечений**: `validate_non_overlapping(segments: list[SegmentRecord])`

### `FileAuditRecord`
Результат аудита WAV-файла (TASK-01).

**Поля**:
- `file_id: str` — идентификатор файла
- `file_path: str` — путь к файлу
- `duration_sec: float` — длительность (секунды)
- `sample_rate: int` — частота дискретизации (Гц)
- `n_channels: int` — количество каналов
- `bit_depth: int` — разрядность
- `file_size_bytes: int` — размер файла (байты)
- `is_valid: bool` — флаг валидности
- `warnings: tuple[str, ...]` — предупреждения
- `subject_id: str | None` — респондент (UNKNOWN до получения реальных данных)
- `task_type: str` — тип задачи (по умолчанию `"UNKNOWN"`)

### `FrameFeatureRecord`
Метаданные кадровых признаков (TASK-02). Фактические данные хранятся в `.parquet` или `.npy`.

**Поля**:
- `file_id: str` — идентификатор файла
- `subject_id: str | None` — респондент
- `task_type: str` — тип задачи
- `sample_rate: int` — частота дискретизации (Гц)
- `frame_ms: float` — длина кадра (мс)
- `hop_ms: float` — шаг кадра (мс)
- `n_frames: int` — количество кадров
- `feature_names: tuple[str, ...]` — названия признаков
- `feature_versions: dict[str, str]` — версии признаков (например, `{"log_mel": "0.1.0", "mfcc": "0.1.0"}`)
- `checksum_audio: str` — hash входного аудио
- `checksum_config: str` — hash конфигурации признаков

### `ExperimentRecord`
Результат эксперимента с фиксацией сплитов, метрик и config hash (TASK-10).

**Поля**:
- `experiment_id: str` — идентификатор эксперимента
- `config_hash: str` — hash конфигурации
- `dataset_version: str` — версия датасета
- `train_subjects: tuple[str, ...]` — респонденты для обучения
- `val_subjects: tuple[str, ...]` — респонденты для валидации
- `test_subjects: tuple[str, ...]` — респонденты для тестирования
- `model_name: str` — название модели (например, `"energy"`, `"webrtc"`, `"custom_vad_v1"`)
- `model_version: str` — версия модели
- `metrics: dict[str, float]` — метрики (например, `{"false_pause_precision": 0.85, ...}`)
- `created_at: str` — время создания (ISO8601)
- `notes: str` — доп. информация

## Правила
- **ASSUMPTION / UNKNOWN**: явно маркируются до аудита реальных данных
- **Никаких пересечений**: `validate_non_overlapping` должна вызываться после каждого VAD
- **Версионирование**: `config_hash` и `feature_versions` обязательны для воспроизводимости
