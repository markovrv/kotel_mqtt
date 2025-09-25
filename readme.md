# Kotel MQTT Integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Интеграция Home Assistant для управления [пеллетными котлами фирмы Слон](https://www.slonkirov.ru/) через MQTT с поддержкой Bluetooth-соединения. Разработана для работы с котлами, которые управляются через [специальное приложение](https://github.com/markovrv/kotel_mqtt_service) с MQTT-брокером.

## Особенности

- 📡 Подключение к котлу через MQTT брокер
- 📱 Мониторинг состояния Bluetooth соединения
- 🔧 Управление параметрами котла в реальном времени
- 📊 Отображение основных показателей (температура, уровень пламени и др.)
- 🔄 Автоматическое переподключение при потере связи
- 🎛️ Полная поддержка различных режимов работы (Стоп/Ручной/Авто)

## Установка

1. Скопируйте папку `kotel_mqtt` в директорию `custom_components` вашего Home Assistant
2. Перезагрузите Home Assistant
3. Добавьте интеграцию через интерфейс настроек

## Конфигурация

Добавьте в файл `configuration.yaml`:

```yaml
kotel_mqtt:
  host: "192.168.1.100"  # IP-адрес MQTT брокера
  port: 1883             # Порт MQTT брокера (по умолчанию: 1883)
  username: "user"       # Имя пользователя MQTT (опционально)
  password: "pass"       # Пароль MQTT (опционально)
  polling_interval: 10   # Интервал опроса в секундах (по умолчанию: 10)
  mqtt_topic_prefix: "kotel"  # Префикс MQTT топиков (по умолчанию: "kotel")
  bluetooth_timeout: 10  # Таймаут Bluetooth в секундах (по умолчанию: 10)
```

## Сущности

После установки интеграция создаст следующие сущности:

### Сенсоры
- **Температура котла** - текущая температура теплоносителя
- **Уровень пламени** - уровень пламени в единицах ADC
- **Номер точки автомата** - текущая точка автоматического режима
- **Статус MQTT подключения** - состояние соединения с MQTT брокером
- **Статус Bluetooth подключения** - состояние Bluetooth соединения с котлом
- **Время последнего сообщения** - время получения последнего сообщения от котла

### Числовые параметры
- **Подача топлива** - длительность подачи топлива (0-60 сек)
- **Пауза** - длительность паузы между подачами (0-120 сек)
- **Скорость вентилятора** - скорость вентилятора (0-25%)
- **Установка термостата** - целевая температура термостата (10-90°C)
- **Температура стабилизации** - температура стабилизации в автоматическом режиме (10-90°C)

### Переключатели
- **Розжиг котла** - включение/выключение розжига

### Селекторы
- **Режим работы котла** - выбор режима работы (Стоп/Ручной/Авто)

### Кнопки
- **Переподключить Bluetooth** - принудительное переподключение Bluetooth соединения

## Сервисы

Интеграция предоставляет следующие сервисы:

### `kotel_mqtt.send_command`
Отправка команды котлу

```yaml
service: kotel_mqtt.send_command
data:
  cmd_type: "set_param"  # или "get_param", "get_var"
  param: "0001"          # код параметра
  value: 30              # значение (только для set_param)
```

### `kotel_mqtt.request_status`
Запрос статуса подключения

### `kotel_mqtt.reconnect_bluetooth`
Переподключение Bluetooth соединения

### `kotel_mqtt.change_parameter`
Изменение параметра с поддержкой дельты

```yaml
service: kotel_mqtt.change_parameter
data:
  param: "0003"  # код параметра
  delta: 1       # изменение на указанное значение
  # или
  value: 15      # установка конкретного значения
```

## Автоматизации

Пример автоматизации для уведомления о потере связи:

```yaml
automation:
  - alias: "Kotel Bluetooth Disconnected"
    trigger:
      platform: state
      entity_id: sensor.kotel_bluetooth_status
      to: "Отключено"
    action:
      - service: notify.mobile_app
        data:
          message: "Котел потерял Bluetooth соединение!"
```

## Панели

Пример панели для отображения параметров котла

```yaml
views:
  - title: Пеллетный котёл
    icon: mdi:fire
    cards: []
    type: sections
    sections:
      - type: grid
        cards:
          - type: heading
            heading_style: title
            heading: Статус котла
          - type: horizontal-stack
            cards:
              - type: glance
                entities:
                  - entity: select.rezhim_raboty_kotla
                    name: Режим
                  - entity: sensor.temperatura_kotla
                    name: Температура
                  - entity: sensor.uroven_plameni
                    name: Пламя
                  - entity: sensor.status_bluetooth
                    name: Bluetooth
          - type: horizontal-stack
            cards:
              - show_name: true
                show_icon: true
                type: button
                name: Выкл.
                icon: mdi:power-off
                tap_action:
                  action: perform-action
                  target:
                    entity_id:
                      - select.rezhim_raboty_kotla
                  data:
                    option: Стоп
                  perform_action: select.select_option
                hold_action:
                  action: more-info
                icon_height: 30px
                entity: select.rezhim_raboty_kotla
              - show_name: true
                show_icon: true
                type: button
                name: Ручной
                icon: mdi:account-cog
                tap_action:
                  action: perform-action
                  target:
                    entity_id:
                      - select.rezhim_raboty_kotla
                  data:
                    option: Ручной
                  perform_action: select.select_option
                hold_action:
                  action: more-info
                icon_height: 30px
                entity: select.rezhim_raboty_kotla
              - show_name: true
                show_icon: true
                type: button
                name: Авто
                icon: mdi:robot
                tap_action:
                  action: perform-action
                  target:
                    entity_id:
                      - select.rezhim_raboty_kotla
                  data:
                    option: Авто
                  perform_action: select.select_option
                hold_action:
                  action: more-info
                icon_height: 30px
                entity: select.rezhim_raboty_kotla
              - show_name: true
                show_icon: true
                type: button
                entity: switch.rozzhig_kotla
                name: Розжиг
            visibility:
              - condition: state
                entity: sensor.status_bluetooth
                state: Подключено
          - type: conditional
            conditions:
              - condition: state
                entity: sensor.status_bluetooth
                state_not: Подключено
            card:
              type: markdown
              content: >
                ## 🛑 Режим: **НЕДОСТУПЕН**

                Котёл отключен от сервера. Возможно, выключен, или потерял
                связь. Если котёл включен, попробуйте **переподключить
                Bluetooth**.
          - type: conditional
            conditions:
              - condition: and
                conditions:
                  - condition: state
                    entity: sensor.status_bluetooth
                    state: Подключено
                  - condition: state
                    entity: select.rezhim_raboty_kotla
                    state: Стоп
            card:
              type: markdown
              content: |
                ## 🛑 Режим: **ВЫКЛЮЧЕН**
                Котел полностью остановлен. Все функции отключены.
          - type: conditional
            conditions:
              - condition: and
                conditions:
                  - condition: state
                    entity: select.rezhim_raboty_kotla
                    state: Ручной
                  - condition: state
                    entity: sensor.status_bluetooth
                    state: Подключено
            card:
              type: markdown
              content: |
                ## 👤 Режим: **РУЧНОЙ**
                Ручное управление параметрами.
          - type: conditional
            conditions:
              - condition: and
                conditions:
                  - condition: state
                    entity: select.rezhim_raboty_kotla
                    state: Авто
                  - condition: state
                    entity: sensor.status_bluetooth
                    state: Подключено
            card:
              type: markdown
              content: >
                ## 🤖 Режим: **АВТОМАТИЧЕСКИЙ**

                Котел работает по программе. Установите температуру
                стабилизации.
          - type: tile
            entity: button.perepodkliuchit_bluetooth
            features_position: bottom
            vertical: false
            grid_options:
              columns: 12
              rows: 1
            show_entity_picture: false
            visibility:
              - condition: and
                conditions:
                  - condition: state
                    entity: select.rezhim_raboty_kotla
                    state: Стоп
                  - condition: state
                    entity: sensor.status_bluetooth
                    state: Подключено
      - type: grid
        cards:
          - type: heading
            heading: Настройка котла
            heading_style: title
          - type: tile
            entity: button.perepodkliuchit_bluetooth
            features_position: bottom
            vertical: false
            grid_options:
              columns: 12
              rows: 1
            show_entity_picture: false
        visibility:
          - condition: state
            entity: sensor.status_bluetooth
            state_not: Подключено
      - type: grid
        cards:
          - type: heading
            heading: Настройки котла
            heading_style: title
          - type: conditional
            conditions:
              - condition: state
                entity: select.rezhim_raboty_kotla
                state: Авто
            card:
              square: true
              type: grid
              columns: 3
              cards:
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:thermometer-minus
                  tap_action:
                    action: perform-action
                    data:
                      param: '0015'
                      delta: -1
                    perform_action: kotel_mqtt.change_parameter
                    target: {}
                - graph: line
                  type: sensor
                  entity: number.temperatura_stabilizatsii
                  detail: 1
                  name: Термостат
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:thermometer-plus
                  tap_action:
                    action: perform-action
                    data:
                      param: '0015'
                      delta: 1
                    perform_action: kotel_mqtt.change_parameter
                    target: {}
          - type: conditional
            conditions:
              - condition: state
                entity: select.rezhim_raboty_kotla
                state: Ручной
            card:
              square: true
              type: grid
              columns: 3
              cards:
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:thermometer-minus
                  tap_action:
                    action: perform-action
                    data:
                      param: '0004'
                      delta: -1
                    perform_action: kotel_mqtt.change_parameter
                    target: {}
                - graph: line
                  type: sensor
                  entity: number.ustanovka_termostata
                  detail: 1
                  name: Термостат
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:thermometer-plus
                  tap_action:
                    action: perform-action
                    data:
                      param: '0004'
                      delta: 1
                    perform_action: kotel_mqtt.change_parameter
                    target: {}
          - type: conditional
            conditions:
              - condition: state
                entity: select.rezhim_raboty_kotla
                state: Ручной
            card:
              type: grid
              columns: 3
              cards:
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:minus
                  tap_action:
                    action: call-service
                    service: kotel_mqtt.change_parameter
                    data:
                      param: '0001'
                      delta: -1
                - graph: line
                  type: sensor
                  entity: number.podacha_topliva
                  detail: 1
                  name: Подача
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:plus
                  tap_action:
                    action: call-service
                    service: kotel_mqtt.change_parameter
                    data:
                      param: '0001'
                      delta: 1
          - type: conditional
            conditions:
              - condition: state
                entity: select.rezhim_raboty_kotla
                state: Ручной
            card:
              type: grid
              columns: 3
              cards:
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:minus
                  tap_action:
                    action: call-service
                    service: kotel_mqtt.change_parameter
                    data:
                      param: '0002'
                      delta: -1
                - graph: line
                  type: sensor
                  entity: number.pauza
                  detail: 1
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:plus
                  tap_action:
                    action: call-service
                    service: kotel_mqtt.change_parameter
                    data:
                      param: '0002'
                      delta: 1
          - type: conditional
            conditions:
              - condition: state
                entity: select.rezhim_raboty_kotla
                state: Ручной
            card:
              type: grid
              columns: 3
              cards:
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:minus
                  tap_action:
                    action: call-service
                    service: kotel_mqtt.change_parameter
                    data:
                      param: '0003'
                      delta: -1
                - graph: line
                  type: sensor
                  entity: number.skorost_ventiliatora
                  detail: 1
                  name: Вентилятор
                - show_name: true
                  show_icon: true
                  type: button
                  icon: mdi:plus
                  tap_action:
                    action: call-service
                    service: kotel_mqtt.change_parameter
                    data:
                      param: '0003'
                      delta: 1
          - graph: line
            type: sensor
            entity: sensor.nomer_tochki_avtomata
            visibility:
              - condition: state
                entity: select.rezhim_raboty_kotla
                state: Авто
            detail: 1
            grid_options:
              columns: 12
              rows: 2
          - type: tile
            entity: button.perepodkliuchit_bluetooth
            features_position: bottom
            vertical: false
            grid_options:
              columns: 12
              rows: 1
            show_entity_picture: false
        visibility:
          - condition: and
            conditions:
              - condition: state
                entity: select.rezhim_raboty_kotla
                state_not: Стоп
              - condition: state
                entity: sensor.status_bluetooth
                state: Подключено
      - type: grid
        cards:
          - type: heading
            heading: Графики
            heading_style: title
          - type: vertical-stack
            cards:
              - type: history-graph
                entities:
                  - entity: sensor.temperatura_kotla
                    name: Температура
                hours_to_show: 24
                refresh_interval: 0
          - type: vertical-stack
            cards:
              - type: history-graph
                entities:
                  - entity: sensor.uroven_plameni
                    name: Уровень пламени
                hours_to_show: 24
                refresh_interval: 0
    header: {}
    badges: []
    max_columns: 2
```

## Поддержка

Если у вас возникли проблемы или вопросы:
1. Проверьте логи Home Assistant на наличие ошибок
2. Убедитесь, что MQTT брокер доступен и правильно настроен
3. Проверьте корректность конфигурации в configuration.yaml

## Разработка

Разработчик: [@markovrv](https://github.com/markovrv)

Для разработки и внесения изменений:
1. Клонируйте репозиторий
2. Установите зависимости
3. Создайте ветку для новой функциональности
4. Отправьте pull request

## Лицензия

Этот проект распространяется под лицензией MIT.

---

**Важно**: Эта интеграция требует наличия работающего MQTT брокера и совместимого котла с поддержкой MQTT протокола.

**Ссылка на MQTT хаб котла: [@markovrv](https://github.com/markovrv/kotel_mqtt_service)**
