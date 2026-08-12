
# GNOME‑Boxes Tool  

### Grafische Installation, Deinstallation & Diagnose für Ubuntu/Debian  

## Version 1.0 

## 📝 Lizenz: MIT

## Entwickler: evilware666 & Helga

## 📦 Überblick

Das **GNOME‑Boxes Tool** ist ein modernes GTK4/Libadwaita‑Programm, das Linux‑Einsteigern und Power‑Usern eine komfortable grafische Oberfläche zur Verwaltung von GNOME Boxes bietet.

Es ersetzt komplizierte Terminalbefehle durch eine intuitive GUI und führt alle notwendigen Systemprüfungen automatisch durch.

---

## ✨ Funktionen

### 🖥️ Installation
- GNOME Boxes  
- QEMU + qemu-utils  
- KVM  
- libvirt (Daemon + Clients)  
- SPICE‑WebDAV & SPICE‑vdagent  
- Automatische Gruppen‑Konfiguration (`kvm`, `libvirt`)  
- Fortschrittsanzeige & Schritt‑Erklärungen  
- Passwortabfrage über GTK4 (kein Terminal nötig)

### 🗑️ Deinstallation
- Vollständige Entfernung aller GNOME‑Boxes‑Pakete  
- Automatisches `autoremove`  
- Virtuelle Maschinen bleiben erhalten  
  (`~/.local/share/gnome-boxes/images/`)

### 🔍 Diagnose
Umfassende Systemprüfung mit klaren Ergebnissen:

- KVM‑Unterstützung  
- KVM‑Modul geladen?  
- Gruppenmitgliedschaft  
- libvirt‑Dienst aktiv?  
- libvirt funktionsfähig?  
- SPICE‑Komponenten installiert?  
- SPICE‑Agent läuft?  
- GNOME Boxes installiert?  
- Virt‑Manager installiert?  
- QEMU & qemu-utils vorhanden?  
- Internetverbindung  
- `/dev/kvm` vorhanden?  

Alle Ergebnisse werden farblich markiert (OK, Warnung, Fehler).

---

## 🧰 Voraussetzungen

- Ubuntu oder Debian (alle aktuellen Versionen)  
- GTK4 + Libadwaita  
- sudo‑Rechte  
- funktionierende Internetverbindung für Installationen  

---

## 🚀 Installation des Tools

```bash
python3 gnome_boxes_tool.py
```

Keine zusätzlichen Abhängigkeiten notwendig — alles wird über Python + GTK4 bereitgestellt.

---

## 🔐 Passworthandling

Das Tool nutzt eine sichere GTK4‑Passwortabfrage:

- Passwort wird **nicht gespeichert**  
- Passwort wird **nur im RAM gehalten**  
- sudo‑Befehle laufen über `sudo -S`  
- Nach Programmende wird das Passwort gelöscht  

---

## 🧩 Architektur

- **GTK4 + Libadwaita**  
- Multi‑Threading für Installationsprozesse  
- Keine veralteten GTK3‑Methoden (z. B. kein `get_children()`)  
- Vollständig kompatibel mit Wayland & X11  

---

## 📁 Code‑Struktur

```
gnome_boxes_tool.py
 ├── Diagnose‑Funktionen
 ├── Installations‑Thread
 ├── Deinstallations‑Thread
 ├── Virt‑Manager‑Installations‑Thread
 ├── GTK4‑Fenster (ToolWindow)
 └── Hilfsfunktionen (KVM, libvirt, QEMU, SPICE, Internet)
```

---





