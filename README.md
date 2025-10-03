# ⚡ Home Assistant Custom Component: Geekworm X728 UPS
(used template: Suptronics UPS X120x Home Assistant Integration, https://github.com/soukal24/ha_suptronics_ups_x120x)

Diese Integration (Custom Component) ermöglicht die direkte Überwachung und Steuerung des **Geekworm X728 UPS HAT** auf Home Assistant OS (HAOS) Systemen, die auf einem Raspberry Pi laufen.

Sie ersetzt die Notwendigkeit eines separaten Add-ons und nutzt direkt die Host-Funktionen (GPIO und I2C) des Betriebssystems.

## 🚀 Funktionen

* **Batterie-Monitoring:** Liest Batteriespannung und Kapazität über I2C (`0x36`, Bus `1`).
* **AC Loss Detection:** Überwacht **GPIO 6** auf Netzstromausfälle und erstellt einen `binary_sensor`.
* **Safe Shutdown Trigger:** Bietet einen `switch` Entität, der bei Aktivierung einen **3-sekündigen HIGH-Puls** an **GPIO 26** sendet, um den Host-Shutdown zu initiieren.
* **Direkter Host-Zugriff:** Nutzt die `smbus2` und `gpiod` Bibliotheken für eine stabile Kommunikation.

## ⚙️ Voraussetzungen

1.  **Home Assistant OS auf Raspberry Pi** (Der Zugriff auf GPIO und I2C wird benötigt).
2.  **I2C-Aktivierung** auf dem Host-System (siehe Installationsschritte).
3.  **Host-Zugriff** auf I2C und GPIO über HAOS (wird durch die vorbereitenden Schritte sichergestellt).

## 🛠️ Installation

### 1. I2C-Aktivierung (Obligatorisch)

Damit die Integration auf I2C (`/dev/i2c-1`) und GPIO (`/dev/gpiochip0`) zugreifen kann, müssen Sie diese auf dem Host-System freigeben:

* **`config.txt`:** Stellen Sie sicher, dass in der Datei `/boot/config.txt` die Zeile `dtparam=i2c_arm=on` vorhanden ist.
* **HAOS Modul:** Navigieren Sie im Home Assistant Konfigurationsordner (`/config`) und erstellen Sie den Unterordner `modules`. Fügen Sie in diesem Ordner eine leere Datei namens `i2c-dev` hinzu (oder stellen Sie sicher, dass die Datei das Wort `i2c-dev` enthält).
* **Host-Neustart:** Führen Sie einen vollständigen **Host-Neustart** durch, damit die Änderungen wirksam werden.

### 2. Custom Component installieren

1.  Navigieren Sie zum Home Assistant Konfigurationsverzeichnis (`/config`).
2.  Erstellen Sie den Ordner **`custom_components`**.
3.  Erstellen Sie darin den Ordner **`geekworm_ups_x728`**.
4.  Kopieren Sie alle generierten Dateien (`__init__.py`, `manifest.json`, `hub.py`, `sensor.py`, `binary_sensor.py`, `switch.py`, `config_flow.py`) in diesen Ordner.
5.  Führen Sie einen weiteren **Home Assistant Server Neustart** durch (nicht den Host, nur den Server).

### 3. Integration Hinzufügen

1.  Gehen Sie zu **Einstellungen** ⚙️ > **Geräte & Dienste**.
2.  Klicken Sie auf **Integration hinzufügen**.
3.  Suchen Sie nach **`Geekworm X728 UPS`**.
4.  Folgen Sie dem Konfigurations-Flow.

## 💡 Beispiel-Automatisierung für Safe Shutdown

Verwenden Sie die erstellten Entitäten, um Ihren Home Assistant Host sicher herunterzufahren:

**Trigger:** `binary_sensor.ups_ac_power_status` wechselt von `on` zu `off` (AC Lost) für 1 Minute.
**Aktion:**
1.  Home Assistant Host sicher herunterfahren (`hassio.host_shutdown`).
2.  Den `switch.ups_safe_shutdown_trigger` (GPIO 26) aktivieren, um den X728-HAT in den Low-Power-Modus zu versetzen.

```yaml
alias: UPS Save Shutdown
description: ""
triggers:
  - trigger: state
    entity_id:
      - binary_sensor.ups_ac_power_status
    from: "on"
    to: "off"
    for:
      hours: 0
      minutes: 1
      seconds: 0
conditions: []
actions:
  - action: telegram_bot.send_message
    metadata: {}
    data:
      config_entry_id: xxxxxxxxxxxxxxxxxxxxxxxxx
      title: ⚠️⚠️ Achtung kritische Spannungsversorgung ⚠️⚠️
      message: Homeassistant wird jetzt herunter gefahren.
  - action: hassio.host_shutdown
    metadata: {}
    data: {}
  - action: switch.turn_on
    metadata: {}
    data: {}
    target:
      entity_id: switch.ups_safe_shutdown_trigger
mode: single

```
