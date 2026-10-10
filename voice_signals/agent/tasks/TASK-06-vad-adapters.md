# TASK-06. Унифицированные адаптеры VAD: energy, WebRTC, Silero

Роль: VAD integration agent. Файлы результата: `vad_base.py`, `energy_vad.py`, `webrtc_vad_adapter.py`, `silero_vad_adapter.py`.

## Цель
Единый интерфейс для сравнения energy baseline, WebRTC VAD, Silero VAD и будущего гибридного сегментатора. Без него нельзя корректно сравнить false pause rate и hesitation recall.

## Вход
Аудиофайл или массив, конфиг backend, ожидаемый sample rate.

## Выход
Список `SegmentRecord` с полями: file_id, subject_id, task_type, start_sec, end_sec, label, score, source_backend, is_pseudo_label=false, notes.

Бинарные метки на этом этапе: `speech`, `non_speech`. Разделение `non_speech` на silent_pause, hesitation, artifact делает TASK-07, не этот модуль.

## Интерфейс
```python
class VadBackend:
    name: str
    version: str
    def process_file(self, path, config) -> List[SegmentRecord]: ...
    def process_array(self, audio, sample_rate, config) -> List[SegmentRecord]: ...
```

## Адаптеры
- Energy VAD: кадровая энергия, адаптивный порог, гистерезис, минимальная длительность речи и паузы. Без внешних нативных зависимостей.
- WebRTC VAD: aggressiveness 0..3, frame_ms 10/20/30, sample_rate 8000/16000/32000/48000. Чувствителен к PCM и sample rate — конвертировать явно и проверять поддержку.
- Silero VAD: официальная модель, параметры sampling_rate, threshold, min_speech_duration_ms, min_silence_duration_ms, speech_pad_ms, window_size. Нормализовать вероятности в сегменты.

## Шаги
1. Базовый класс `VadBackend`.
2. Конвертация: mono, ресемплинг, нужный PCM, сохранение исходного sample rate в метаданных.
3. Непересекающиеся сегменты speech; покадровые вероятности переводятся в сегменты гистерезисом.
4. Версионирование: backend_name, backend_version, model_version, config_hash (особенно фиксировать версию Silero).
5. Ошибки: неподдерживаемый файл — понятная ошибка или пустой результат с флагом, без молчаливого искажения.

## Критерии приёмки
1. Одинаковая schema у всех backend.
2. Сегменты монотонны и не пересекаются.
3. Время в секундах исходного файла, не в кадрах.
4. WebRTC и Silero работают на 8 и 16 kHz.
5. Energy VAD без внешних нативных зависимостей.
6. Запуск в Colab T4 и локально на CPU.
7. Сериализация в CSV, Parquet или JSON.

## Тесты
- Чередование тона и тишины даёт ожидаемые speech-сегменты.
- Полная тишина — пустой список.
- Очень короткий файл без ошибки.
- Стерео конвертируется в mono.
- Неизвестный sample rate: явная ошибка или автоконверсия по config.
- Comparison: три backend на одном файле дают один формат.
- Regression: эталонные сегменты для небольшого файла.

## Ошибки, которых избегать
- Разные единицы времени.
- Забытый stereo -> mono.
- Нефиксированная версия Silero.
- Передача WebRTC неподдерживаемого формата.
- Автоматическое считывание `non_speech` как `silent_pause`.

## Инструкция агенту
Реализуй VadBackend и адаптеры energy, WebRTC и Silero. Вход — файл или массив, выход — непересекающиеся speech-сегменты в формате SegmentRecord с версией backend и конфигом. Тесты на синтетике с речеподобными фрагментами и тишиной. Не смешивай бинарный VAD с многоклассовой таксономией.
