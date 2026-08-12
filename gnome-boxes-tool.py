#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GNOME‑Boxes Tool – GTK4/Libadwaita
===========================================
Grafische Installation, Diagnose & Deinstallation
für GNOME Boxes unter Ubuntu & Debian.

Version      : 1.0
Kompatibel   : Vollständig GTK4 (ohne get_children)
Features     :
    • Installation aller Virtualisierungs‑Komponenten
      (GNOME Boxes, QEMU, KVM, libvirt, SPICE, qemu-utils)
    • Deinstallation inkl. Bereinigung
    • System‑Diagnose (KVM, libvirt, SPICE, QEMU, Gruppen)
    • Passwortdialog (GTK4) ohne Terminal
    • Fortschrittsanzeige & Statusmeldungen

Autoren      : evilware666 & Helga
Lizenz       : MIT
"""
import sys
import os
import subprocess
import threading

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

# ====================== Hilfsfunktionen ======================

def get_user():
    user = os.getenv('SUDO_USER') or os.getenv('USER')
    if not user:
        raise Exception("Der aktuelle Benutzer konnte nicht ermittelt werden.")
    return user

def detect_cpu_vendor():
    try:
        with open('/proc/cpuinfo', 'r') as f:
            cpuinfo = f.read()
        if 'GenuineIntel' in cpuinfo or 'vmx' in cpuinfo:
            return 'intel'
        if 'AuthenticAMD' in cpuinfo or 'svm' in cpuinfo:
            return 'amd'
        return None
    except Exception:
        return None

def is_kvm_module_loaded():
    try:
        result = subprocess.run(['lsmod'], capture_output=True, text=True, timeout=5)
        return 'kvm ' in result.stdout
    except:
        return False

def kvm_fallback_check():
    if os.path.exists('/dev/kvm'):
        return True
    if is_kvm_module_loaded():
        return True
    try:
        result = subprocess.run(['virt-host-validate'], capture_output=True, text=True, timeout=5)
        return "PASS" in result.stdout
    except:
        return False

def check_kvm_support():
    try:
        if os.path.exists('/usr/sbin/kvm-ok') or os.path.exists('/usr/bin/kvm-ok'):
            result = subprocess.run(['kvm-ok'], capture_output=True, text=True, timeout=5)
            if 'KVM acceleration can be used' in result.stdout:
                return True
    except:
        pass
    return kvm_fallback_check()

def check_user_in_groups():
    user = get_user()
    try:
        result = subprocess.run(['id', '-nG', user], capture_output=True, text=True, timeout=5)
        groups = result.stdout.split()
        return 'kvm' in groups and 'libvirt' in groups
    except:
        return False

def is_package_installed(package):
    try:
        result = subprocess.run(['dpkg', '-l', package], capture_output=True, text=True, timeout=10)
        for line in result.stdout.splitlines():
            if line.startswith('ii') and package in line:
                return True
        return False
    except:
        return False

def is_gnome_boxes_installed():
    return is_package_installed('gnome-boxes')

def is_virt_manager_installed():
    return is_package_installed('virt-manager')

def has_internet_connection():
    try:
        subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'], capture_output=True, timeout=3)
        return True
    except:
        pass
    try:
        result = subprocess.run(['curl', '-Is', 'https://ubuntu.com'], capture_output=True, text=True, timeout=5)
        return "HTTP" in result.stdout
    except:
        return False

def is_spice_agent_running():
    try:
        result = subprocess.run(['systemctl', 'is-active', 'spice-vdagentd'], capture_output=True, text=True, timeout=5)
        return 'active' in result.stdout
    except:
        return False

def qemu_version():
    try:
        result = subprocess.run(['qemu-system-x86_64', '--version'], capture_output=True, text=True, timeout=5)
        return result.stdout.strip()
    except:
        return None

def libvirt_functional():
    try:
        result = subprocess.run(['virsh', 'list'], capture_output=True, text=True, timeout=5)
        return "Id" in result.stdout or "Name" in result.stdout
    except:
        return False

# ====================== Diagnose-Daten sammeln ======================

def run_diagnostic_checks():
    """Führt alle Prüfungen durch und gibt eine Liste von Ergebnissen zurück."""
    results = []

    # KVM-Unterstützung
    if check_kvm_support():
        results.append({
            'id': 'kvm_support',
            'name': 'KVM-Unterstützung',
            'status': 'ok',
            'message': 'KVM wird unterstützt',
            'package': None
        })
    else:
        results.append({
            'id': 'kvm_support',
            'name': 'KVM-Unterstützung',
            'status': 'error',
            'message': 'KVM wird nicht unterstützt – Virtualisierung im BIOS aktivieren?',
            'package': None
        })

    # KVM-Modul geladen
    if is_kvm_module_loaded():
        results.append({
            'id': 'kvm_module',
            'name': 'KVM-Modul',
            'status': 'ok',
            'message': 'KVM-Modul ist geladen',
            'package': None
        })
    else:
        results.append({
            'id': 'kvm_module',
            'name': 'KVM-Modul',
            'status': 'warning',
            'message': 'KVM-Modul nicht geladen',
            'package': None
        })

    # Gruppenmitgliedschaft
    if check_user_in_groups():
        results.append({
            'id': 'groups',
            'name': 'Gruppen kvm/libvirt',
            'status': 'ok',
            'message': 'Benutzer ist in den Gruppen',
            'package': None
        })
    else:
        results.append({
            'id': 'groups',
            'name': 'Gruppen kvm/libvirt',
            'status': 'error',
            'message': 'Benutzer nicht in kvm/libvirt',
            'package': None
        })

    # libvirt-Dienst
    try:
        res = subprocess.run(['systemctl', 'is-active', 'libvirtd'], capture_output=True, text=True, timeout=5)
        if 'active' in res.stdout:
            results.append({
                'id': 'libvirt_service',
                'name': 'libvirt-Dienst',
                'status': 'ok',
                'message': 'libvirt läuft',
                'package': None
            })
        else:
            results.append({
                'id': 'libvirt_service',
                'name': 'libvirt-Dienst',
                'status': 'error',
                'message': 'libvirt läuft nicht',
                'package': None
            })
    except:
        results.append({
            'id': 'libvirt_service',
            'name': 'libvirt-Dienst',
            'status': 'error',
            'message': 'libvirt konnte nicht geprüft werden',
            'package': None
        })

    # libvirt funktional
    if libvirt_functional():
        results.append({
            'id': 'libvirt_functional',
            'name': 'libvirt funktionsfähig',
            'status': 'ok',
            'message': 'virsh list funktioniert',
            'package': None
        })
    else:
        results.append({
            'id': 'libvirt_functional',
            'name': 'libvirt funktionsfähig',
            'status': 'warning',
            'message': 'libvirt funktioniert nicht (virsh list fehlgeschlagen)',
            'package': None
        })

    # SPICE-Komponenten
    for pkg, desc in [('spice-webdavd', 'SPICE-WebDAV (Ordnerfreigabe)'),
                      ('spice-vdagent', 'SPICE-vdagent (Integration)')]:
        if is_package_installed(pkg):
            results.append({
                'id': f'pkg_{pkg}',
                'name': desc,
                'status': 'ok',
                'message': 'installiert',
                'package': pkg
            })
        else:
            results.append({
                'id': f'pkg_{pkg}',
                'name': desc,
                'status': 'warning',
                'message': 'fehlt',
                'package': pkg
            })

    # SPICE-Agent-Dienst
    if is_spice_agent_running():
        results.append({
            'id': 'spice_agent',
            'name': 'SPICE-Agent-Dienst',
            'status': 'ok',
            'message': 'läuft',
            'package': None
        })
    else:
        results.append({
            'id': 'spice_agent',
            'name': 'SPICE-Agent-Dienst',
            'status': 'warning',
            'message': 'läuft nicht',
            'package': None
        })

    # GNOME Boxes
    if is_gnome_boxes_installed():
        results.append({
            'id': 'gnome_boxes',
            'name': 'GNOME Boxes',
            'status': 'ok',
            'message': 'installiert',
            'package': 'gnome-boxes'
        })
    else:
        results.append({
            'id': 'gnome_boxes',
            'name': 'GNOME Boxes',
            'status': 'warning',
            'message': 'nicht installiert',
            'package': 'gnome-boxes'
        })

    # Virt-Manager (mit Hinweis für Anfänger)
    if is_virt_manager_installed():
        results.append({
            'id': 'virt_manager',
            'name': 'Virt-Manager (für Anfänger NICHT empfohlen)',
            'status': 'ok',
            'message': 'installiert',
            'package': 'virt-manager'
        })
    else:
        results.append({
            'id': 'virt_manager',
            'name': 'Virt-Manager (für Anfänger NICHT empfohlen)',
            'status': 'warning',
            'message': 'nicht installiert',
            'package': 'virt-manager'
        })

    # QEMU
    if is_package_installed('qemu-system-x86'):
        results.append({
            'id': 'qemu',
            'name': 'QEMU',
            'status': 'ok',
            'message': 'installiert',
            'package': 'qemu-system-x86'
        })
    else:
        results.append({
            'id': 'qemu',
            'name': 'QEMU',
            'status': 'error',
            'message': 'fehlt (notwendig)',
            'package': 'qemu-system-x86'
        })

    # qemu-utils
    if is_package_installed('qemu-utils'):
        results.append({
            'id': 'qemu_utils',
            'name': 'qemu-utils (Festplatten-Images)',
            'status': 'ok',
            'message': 'installiert',
            'package': 'qemu-utils'
        })
    else:
        results.append({
            'id': 'qemu_utils',
            'name': 'qemu-utils (Festplatten-Images)',
            'status': 'warning',
            'message': 'fehlt – VM-Erstellung kann fehlschlagen',
            'package': 'qemu-utils'
        })

    # Internetverbindung
    if has_internet_connection():
        results.append({
            'id': 'internet',
            'name': 'Internetverbindung',
            'status': 'ok',
            'message': 'verbunden',
            'package': None
        })
    else:
        results.append({
            'id': 'internet',
            'name': 'Internetverbindung',
            'status': 'warning',
            'message': 'nicht erreichbar – Installationen nicht möglich',
            'package': None
        })

    # /dev/kvm
    if os.path.exists('/dev/kvm'):
        results.append({
            'id': 'dev_kvm',
            'name': '/dev/kvm',
            'status': 'ok',
            'message': 'vorhanden',
            'package': None
        })
    else:
        results.append({
            'id': 'dev_kvm',
            'name': '/dev/kvm',
            'status': 'warning',
            'message': 'fehlt – KVM möglicherweise nicht aktiv',
            'package': None
        })

    return results

# ====================== Thread für Paketinstallation ======================

class PackageInstallThread(threading.Thread):
    def __init__(self, password, package, status_callback, finish_callback, error_callback):
        super().__init__()
        self.password = password
        self.package = package
        self.status_callback = status_callback
        self.finish_callback = finish_callback
        self.error_callback = error_callback
        self.daemon = True
        self.process = None

    def run(self):
        try:
            GLib.idle_add(self.status_callback, f"📦 Installiere {self.package} …")
            self._run_sudo_command(['apt', 'update'])
            self._run_sudo_command(['apt', 'install', '-y', self.package])
            GLib.idle_add(self.finish_callback, True)
        except Exception as e:
            GLib.idle_add(self.error_callback, str(e))

    def _run_sudo_command(self, cmd):
        full_cmd = ['sudo', '-S', '-k'] + cmd
        self.process = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = self.process.communicate(input=self.password + '\n')
        if self.process.returncode != 0:
            if 'incorrect password' in stderr.lower() or 'authentication failure' in stderr.lower():
                raise Exception("Das Passwort ist falsch. Bitte versuchen Sie es erneut.")
            else:
                raise Exception(f"Installation von {self.package} fehlgeschlagen:\n{stderr.strip()}")

# ====================== Installations-Thread (GNOME Boxes) ======================

class InstallerThread(threading.Thread):
    def __init__(self, password, status_callback, error_callback,
                 finish_callback, step_explanation_callback, progress_callback):
        super().__init__()
        self.password = password
        self.status_callback = status_callback
        self.error_callback = error_callback
        self.finish_callback = finish_callback
        self.step_explanation_callback = step_explanation_callback
        self.progress_callback = progress_callback
        self.daemon = True
        self._cancel = False
        self.process = None

    def run(self):
        try:
            if not has_internet_connection():
                raise Exception("Keine Internetverbindung. Bitte überprüfe deine Netzwerkverbindung.")

            steps = self._build_steps()
            total = len(steps)
            for i, (description, explanation, cmd) in enumerate(steps):
                if self._cancel:
                    break
                GLib.idle_add(self.status_callback, description)
                GLib.idle_add(self.step_explanation_callback, explanation)
                GLib.idle_add(self.progress_callback, i + 1, total)
                self._run_sudo_command(cmd)
            if not self._cancel:
                GLib.idle_add(self.finish_callback, True)
            else:
                GLib.idle_add(self.finish_callback, False)
        except Exception as e:
            GLib.idle_add(self.error_callback, str(e))

    def _build_steps(self):
        user = get_user()
        steps = [
            ("📦 Paketlisten werden aktualisiert …",
             "Dein System wird auf den neuesten Stand gebracht.",
             ['apt', 'update']),
            ("📥 GNOME Boxes und Werkzeuge werden installiert …",
             "GNOME Boxes, QEMU (inkl. Hilfsprogramme), KVM, libvirt und Virtualisierungswerkzeuge werden installiert.",
             ['apt', 'install', '-y',
              'gnome-boxes', 'qemu-system-x86', 'qemu-utils',
              'libvirt-daemon-system', 'libvirt-clients',
              'bridge-utils', 'virtinst', 'cpu-checker',
              'spice-webdavd', 'spice-vdagent']),
            ("⚙️ libvirt-Dienst wird gestartet …",
             "libvirt wird im Hintergrund gestartet.",
             ['systemctl', 'enable', '--now', 'libvirtd']),
            ("👤 Benutzer wird zu Gruppe 'kvm' hinzugefügt …",
             "Du wirst zur Gruppe 'kvm' hinzugefügt.",
             ['usermod', '-aG', 'kvm', user]),
            ("👤 Benutzer wird zu Gruppe 'libvirt' hinzugefügt …",
             "Du wirst zur Gruppe 'libvirt' hinzugefügt.",
             ['usermod', '-aG', 'libvirt', user]),
            ("🧩 KVM-Kernelmodul wird geprüft …",
             "Prüft, ob das KVM-Modul aktiv ist.",
             ['true']),
        ]
        vendor = detect_cpu_vendor()
        if vendor == 'intel':
            steps.append(("🧩 Intel KVM-Modul wird geprüft …",
                          "Prüft Intel-Virtualisierung.",
                          ['true']))
        elif vendor == 'amd':
            steps.append(("🧩 AMD KVM-Modul wird geprüft …",
                          "Prüft AMD-Virtualisierung.",
                          ['true']))
        steps.append(("✅ Virtualisierungsumgebung wird überprüft …",
                      "Die Virtualisierungsumgebung wurde eingerichtet.",
                      ['kvm-ok']))
        return steps

    def _run_sudo_command(self, cmd):
        full_cmd = ['sudo', '-S', '-k'] + cmd
        self.process = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = self.process.communicate(input=self.password + '\n')
        if self.process.returncode != 0:
            if 'incorrect password' in stderr.lower() or 'authentication failure' in stderr.lower():
                raise Exception("Das Passwort ist falsch. Bitte versuchen Sie es erneut.")
            else:
                user_msg = f"Die Installation konnte nicht abgeschlossen werden.\n\nGrund: {stderr.strip()}"
                if 'modprobe' in ' '.join(cmd) and 'Operation not permitted' in stderr:
                    user_msg += "\n\n💡 Tipp: Stelle sicher, dass die Hardware-Virtualisierung im BIOS/UEFI aktiviert ist."
                raise Exception(user_msg)
        return stdout, stderr

    def cancel(self):
        self._cancel = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                pass

# ====================== Uninstall-Thread (GNOME Boxes) ======================

class UninstallThread(threading.Thread):
    def __init__(self, password, status_callback, error_callback, finish_callback):
        super().__init__()
        self.password = password
        self.status_callback = status_callback
        self.error_callback = error_callback
        self.finish_callback = finish_callback
        self.daemon = True
        self._cancel = False
        self.process = None

    def run(self):
        try:
            GLib.idle_add(self.status_callback, "🗑️ GNOME Boxes wird entfernt …")
            self._run_sudo_command(['apt', 'remove', '--purge', '-y', 'gnome-boxes',
                                    'qemu-utils', 'spice-webdavd', 'spice-vdagent'])
            GLib.idle_add(self.status_callback, "🧹 Nicht mehr benötigte Pakete werden bereinigt …")
            self._run_sudo_command(['apt', 'autoremove', '-y'])
            GLib.idle_add(self.finish_callback, True)
        except Exception as e:
            GLib.idle_add(self.error_callback, str(e))

    def _run_sudo_command(self, cmd):
        full_cmd = ['sudo', '-S', '-k'] + cmd
        self.process = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = self.process.communicate(input=self.password + '\n')
        if self.process.returncode != 0:
            if 'incorrect password' in stderr.lower() or 'authentication failure' in stderr.lower():
                raise Exception("Das Passwort ist falsch. Bitte versuchen Sie es erneut.")
            else:
                raise Exception(f"Die Deinstallation konnte nicht abgeschlossen werden.\n\nGrund: {stderr.strip()}")
        return stdout, stderr

    def cancel(self):
        self._cancel = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                pass

# ====================== Virt-Manager Installations-Thread ======================

class VirtManagerInstallThread(threading.Thread):
    def __init__(self, password, status_callback, error_callback, finish_callback):
        super().__init__()
        self.password = password
        self.status_callback = status_callback
        self.error_callback = error_callback
        self.finish_callback = finish_callback
        self.daemon = True
        self._cancel = False
        self.process = None

    def run(self):
        try:
            if not has_internet_connection():
                raise Exception("Keine Internetverbindung. Bitte überprüfe deine Netzwerkverbindung.")

            GLib.idle_add(self.status_callback, "📦 Paketlisten werden aktualisiert …")
            self._run_sudo_command(['apt', 'update'])
            
            GLib.idle_add(self.status_callback, "🔧 Virt-Manager wird installiert …")
            self._run_sudo_command(['apt', 'install', '-y', 'virt-manager'])
            
            GLib.idle_add(self.finish_callback, True)
        except Exception as e:
            GLib.idle_add(self.error_callback, str(e))

    def _run_sudo_command(self, cmd):
        full_cmd = ['sudo', '-S', '-k'] + cmd
        self.process = subprocess.Popen(
            full_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = self.process.communicate(input=self.password + '\n')
        if self.process.returncode != 0:
            if 'incorrect password' in stderr.lower() or 'authentication failure' in stderr.lower():
                raise Exception("Das Passwort ist falsch. Bitte versuchen Sie es erneut.")
            else:
                raise Exception(f"Die Installation von Virt-Manager konnte nicht abgeschlossen werden.\n\nGrund: {stderr.strip()}")
        return stdout, stderr

    def cancel(self):
        self._cancel = True
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except:
                pass

# ====================== Hauptfenster (GUI) ======================

class ToolWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("GNOME-Boxes Tool")
        self.set_default_size(700, 600)
        self.set_modal(True)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        main_box.set_margin_start(20)
        main_box.set_margin_end(20)
        main_box.set_margin_top(20)
        main_box.set_margin_bottom(20)
        self.set_content(main_box)

        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="GNOME-Boxes Tool"))
        main_box.append(header)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        main_box.append(self.stack)

        # ---- Willkommen ----
        welcome_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        welcome_box.set_halign(Gtk.Align.CENTER)
        welcome_box.set_valign(Gtk.Align.CENTER)

        label_welcome = Gtk.Label()
        label_welcome.set_markup(
            "<big><b>👋 Willkommen beim GNOME-Boxes Tool!</b></big>\n\n"
            "Dieses Tool hilft dir bei der Installation oder Deinstallation von GNOME Boxes.\n\n"
            "Dazu werden folgende Komponenten eingerichtet:\n"
            "• 🖥️  GNOME Boxes – die einfache Virtualisierungssoftware\n"
            "• ⚡ KVM / QEMU – der Turbo-Modus für deine VMs\n"
            "• 🔧 libvirt – die Schaltzentrale für deine VMs\n"
            "• 📁 SPICE-WebDAV und SPICE-vdagent – für bessere Integration\n"
            "• 🗄️  qemu-utils – für volle Festplatten-Image-Unterstützung\n\n"
            "Die Installation benötigt Administratorrechte.\n\n"
            "<i>💡 Tipp: Fahre mit der Maus über die Buttons für Erklärungen.</i>"
        )
        label_welcome.set_justify(Gtk.Justification.CENTER)
        label_welcome.set_wrap(True)
        welcome_box.append(label_welcome)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.CENTER)

        self.btn_start = Gtk.Button(label="Installieren")
        self.btn_start.add_css_class("suggested-action")
        self.btn_start.set_tooltip_text("Startet die Installation von GNOME Boxes und allen benötigten Komponenten.\nDu wirst nach deinem Passwort gefragt.")
        self.btn_start.connect("clicked", self.on_start_clicked)
        btn_box.append(self.btn_start)

        btn_diagnose = Gtk.Button(label="🔍 System prüfen")
        btn_diagnose.add_css_class("pill")
        btn_diagnose.set_tooltip_text("Prüft dein System auf Virtualisierungs-Kompatibilität und zeigt Ergebnisse, Hinweise und Probleme an.")
        btn_diagnose.connect("clicked", self.on_diagnose_clicked)
        btn_box.append(btn_diagnose)

        welcome_box.append(btn_box)

        self.btn_uninstall = Gtk.Button(label="🗑️ GNOME Boxes deinstallieren")
        self.btn_uninstall.add_css_class("destructive-action")
        self.btn_uninstall.set_tooltip_text("Entfernt GNOME Boxes und seine Konfigurationsdateien.\nDeine virtuellen Maschinen bleiben erhalten.")
        self.btn_uninstall.connect("clicked", self.on_uninstall_clicked)
        welcome_box.append(self.btn_uninstall)

        # Beenden-Button
        quit_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        quit_box.set_halign(Gtk.Align.CENTER)
        quit_box.set_margin_top(10)

        btn_quit = Gtk.Button(label="Beenden")
        btn_quit.set_tooltip_text("Schließt das GNOME-Boxes Tool.")
        btn_quit.connect("clicked", lambda x: self.get_application().quit())
        quit_box.append(btn_quit)

        welcome_box.append(quit_box)

        self.stack.add_named(welcome_box, "welcome")

        # ---- Deinstallations-Bestätigung ----
        uninstall_confirm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        uninstall_confirm_box.set_halign(Gtk.Align.CENTER)
        uninstall_confirm_box.set_valign(Gtk.Align.CENTER)
        uninstall_confirm_box.set_margin_start(20)
        uninstall_confirm_box.set_margin_end(20)

        confirm_label = Gtk.Label()
        confirm_label.set_markup(
            "<big><b>⚠️ GNOME Boxes wirklich deinstallieren?</b></big>\n\n"
            "Möchtest du GNOME Boxes und die zugehörigen Systempakete entfernen?\n\n"
            "📁 <b>Deine virtuellen Maschinen werden NICHT gelöscht.</b>\n"
            "   Sie bleiben unter ~/.local/share/gnome-boxes/images/ erhalten.\n\n"
            "🧹 <b>Nicht mehr benötigte Abhängigkeiten</b> werden automatisch entfernt.\n\n"
            "Diese Aktion kann nicht rückgängig gemacht werden."
        )
        confirm_label.set_justify(Gtk.Justification.LEFT)
        confirm_label.set_wrap(True)
        uninstall_confirm_box.append(confirm_label)

        confirm_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        confirm_btn_box.set_halign(Gtk.Align.CENTER)

        btn_confirm_cancel = Gtk.Button(label="❌ Abbrechen")
        btn_confirm_cancel.set_tooltip_text("Bricht die Deinstallation ab und geht zurück zur Startseite.")
        btn_confirm_cancel.connect("clicked", lambda x: self.stack.set_visible_child_name("welcome"))
        confirm_btn_box.append(btn_confirm_cancel)

        btn_confirm_yes = Gtk.Button(label="✅ Ja, deinstallieren")
        btn_confirm_yes.add_css_class("destructive-action")
        btn_confirm_yes.set_tooltip_text("Bestätigt die Deinstallation und führt zur Passwortabfrage.")
        btn_confirm_yes.connect("clicked", self.on_uninstall_confirm_yes)
        confirm_btn_box.append(btn_confirm_yes)

        uninstall_confirm_box.append(confirm_btn_box)
        self.stack.add_named(uninstall_confirm_box, "uninstall_confirm")

        # ---- Passwort (Installation) ----
        password_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        password_box.set_halign(Gtk.Align.CENTER)
        password_box.set_valign(Gtk.Align.CENTER)

        hint_label = Gtk.Label()
        hint_label.set_markup(
            "<b>🔑 Administrator-Passwort erforderlich</b>\n\n"
            "Für die Installation werden erweiterte Rechte benötigt.\n"
            "Bitte gib dein Benutzerpasswort ein – es wird nicht gespeichert."
        )
        hint_label.set_justify(Gtk.Justification.CENTER)
        hint_label.set_wrap(True)
        password_box.append(hint_label)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_placeholder_text("Dein Passwort")
        self.password_entry.set_width_chars(25)
        self.password_entry.set_tooltip_text("Gib hier dein Benutzerpasswort ein.\nEs wird nur für die Installation verwendet und nicht gespeichert.")
        self.password_entry.connect('activate', self.on_password_ok)
        password_box.append(self.password_entry)

        self.password_error = Gtk.Label()
        self.password_error.set_markup('<span foreground="red">❌ Falsches Passwort – bitte erneut versuchen.</span>')
        self.password_error.set_visible(False)
        password_box.append(self.password_error)

        btn_install = Gtk.Button(label="Installation starten")
        btn_install.add_css_class("suggested-action")
        btn_install.set_tooltip_text("Startet die Installation mit dem eingegebenen Passwort.\nDie Installation kann mehrere Minuten dauern.")
        btn_install.connect("clicked", self.on_password_ok)
        password_box.append(btn_install)

        btn_back = Gtk.Button(label="Zurück")
        btn_back.set_tooltip_text("Geht zurück zur Startseite.")
        btn_back.connect("clicked", lambda x: self.stack.set_visible_child_name("welcome"))
        password_box.append(btn_back)

        btn_help = Gtk.Button(label="❓ Hilfe")
        btn_help.set_tooltip_text("Zeigt häufig gestellte Fragen und Lösungen an.")
        btn_help.connect("clicked", self.show_help, "password")
        password_box.append(btn_help)

        self.stack.add_named(password_box, "password")

        # ---- Passwort (Deinstallation) ----
        uninstall_pass_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        uninstall_pass_box.set_halign(Gtk.Align.CENTER)
        uninstall_pass_box.set_valign(Gtk.Align.CENTER)

        hint_uninstall = Gtk.Label()
        hint_uninstall.set_markup(
            "<b>🔑 Administrator-Passwort erforderlich</b>\n\n"
            "Für die Deinstallation werden Administratorrechte benötigt.\n"
            "Bitte gib dein Benutzerpasswort ein – es wird nicht gespeichert.\n\n"
            "<i>Deine virtuellen Maschinen bleiben erhalten.</i>"
        )
        hint_uninstall.set_justify(Gtk.Justification.CENTER)
        hint_uninstall.set_wrap(True)
        uninstall_pass_box.append(hint_uninstall)

        self.uninstall_password_entry = Gtk.Entry()
        self.uninstall_password_entry.set_visibility(False)
        self.uninstall_password_entry.set_placeholder_text("Dein Passwort")
        self.uninstall_password_entry.set_width_chars(25)
        self.uninstall_password_entry.set_tooltip_text("Gib hier dein Benutzerpasswort ein.\nEs wird nur für die Deinstallation verwendet.")
        self.uninstall_password_entry.connect('activate', self.on_uninstall_password_ok)
        uninstall_pass_box.append(self.uninstall_password_entry)

        self.uninstall_password_error = Gtk.Label()
        self.uninstall_password_error.set_markup('<span foreground="red">❌ Falsches Passwort – bitte erneut versuchen.</span>')
        self.uninstall_password_error.set_visible(False)
        uninstall_pass_box.append(self.uninstall_password_error)

        btn_uninstall_go = Gtk.Button(label="Deinstallation starten")
        btn_uninstall_go.add_css_class("destructive-action")
        btn_uninstall_go.set_tooltip_text("Startet die Deinstallation. Dieser Vorgang kann nicht rückgängig gemacht werden.")
        btn_uninstall_go.connect("clicked", self.on_uninstall_password_ok)
        uninstall_pass_box.append(btn_uninstall_go)

        btn_back_uninstall = Gtk.Button(label="Zurück")
        btn_back_uninstall.set_tooltip_text("Geht zurück zur Startseite.")
        btn_back_uninstall.connect("clicked", lambda x: self.stack.set_visible_child_name("welcome"))
        uninstall_pass_box.append(btn_back_uninstall)

        self.stack.add_named(uninstall_pass_box, "uninstall_password")

        # ---- Hinweis: Virt-Manager ----
        virt_manager_hint_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        virt_manager_hint_box.set_halign(Gtk.Align.CENTER)
        virt_manager_hint_box.set_valign(Gtk.Align.CENTER)
        virt_manager_hint_box.set_margin_start(20)
        virt_manager_hint_box.set_margin_end(20)

        virt_hint_label = Gtk.Label()
        virt_hint_label.set_markup(
            "<big><b>⚠️ Virt-Manager – Ein Tool für Fortgeschrittene</b></big>\n\n"
            "Virt-Manager ist ein <b>sehr mächtiges Werkzeug</b> für die Virtualisierung.\n"
            "Es bietet <b>viele erweiterte Einstellungen</b>, die für Anfänger\n"
            "<b>überfordernd</b> sein können.\n\n"
            "🔹 <b>Für wen ist Virt-Manager geeignet?</b>\n"
            "• Fortgeschrittene Nutzer, die mehr Kontrolle über ihre VMs möchten.\n"
            "• Nutzer, die spezielle Netzwerk- oder Speicherkonfigurationen benötigen.\n"
            "• Administratoren, die mehrere VMs verwalten.\n\n"
            "🔹 <b>Für wen ist GNOME Boxes besser geeignet?</b>\n"
            "• Einsteiger, die einfach nur eine VM ausprobieren möchten.\n"
            "• Nutzer, die eine übersichtliche, einfache Oberfläche bevorzugen.\n\n"
            "<b>💡 Tipp:</b> Wenn du mit Virtualisierung noch nicht vertraut bist,\n"
            "ist GNOME Boxes die bessere Wahl. Virt-Manager kannst du später\n"
            "jederzeit nachinstallieren.\n\n"
            "⚠️ <b>Bist du sicher, dass du Virt-Manager installieren möchtest?</b>"
        )
        virt_hint_label.set_justify(Gtk.Justification.LEFT)
        virt_hint_label.set_wrap(True)
        virt_manager_hint_box.append(virt_hint_label)

        btn_virt_hint_ok = Gtk.Button(label="✅ Ja, ich möchte Virt-Manager installieren")
        btn_virt_hint_ok.add_css_class("suggested-action")
        btn_virt_hint_ok.set_tooltip_text("Bestätigt und führt zur Passwortabfrage für Virt-Manager.")
        btn_virt_hint_ok.connect("clicked", self.on_virt_hint_ok_clicked)
        virt_manager_hint_box.append(btn_virt_hint_ok)

        btn_virt_hint_cancel = Gtk.Button(label="❌ Nein, doch nicht")
        btn_virt_hint_cancel.set_tooltip_text("Bricht ab und geht zurück zur Startseite.")
        btn_virt_hint_cancel.connect("clicked", lambda x: self.stack.set_visible_child_name("welcome"))
        virt_manager_hint_box.append(btn_virt_hint_cancel)

        self.stack.add_named(virt_manager_hint_box, "virt_manager_hint")

        # ---- Passwort (Virt-Manager) ----
        virt_manager_pass_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        virt_manager_pass_box.set_halign(Gtk.Align.CENTER)
        virt_manager_pass_box.set_valign(Gtk.Align.CENTER)

        hint_virt = Gtk.Label()
        hint_virt.set_markup(
            "<b>🔑 Administrator-Passwort erforderlich</b>\n\n"
            "Für die Installation von Virt-Manager werden erweiterte Rechte benötigt.\n"
            "Bitte gib dein Benutzerpasswort ein – es wird nicht gespeichert.\n\n"
            "<i>Virt-Manager ist ein fortgeschrittenes Tool mit mehr Einstellungsmöglichkeiten.</i>"
        )
        hint_virt.set_justify(Gtk.Justification.CENTER)
        hint_virt.set_wrap(True)
        virt_manager_pass_box.append(hint_virt)

        self.virt_password_entry = Gtk.Entry()
        self.virt_password_entry.set_visibility(False)
        self.virt_password_entry.set_placeholder_text("Dein Passwort")
        self.virt_password_entry.set_width_chars(25)
        self.virt_password_entry.set_tooltip_text("Gib hier dein Benutzerpasswort ein.\nEs wird nur für die Installation von Virt-Manager verwendet.")
        self.virt_password_entry.connect('activate', self.on_virt_manager_password_ok)
        virt_manager_pass_box.append(self.virt_password_entry)

        self.virt_password_error = Gtk.Label()
        self.virt_password_error.set_markup('<span foreground="red">❌ Falsches Passwort – bitte erneut versuchen.</span>')
        self.virt_password_error.set_visible(False)
        virt_manager_pass_box.append(self.virt_password_error)

        btn_virt_install = Gtk.Button(label="Virt-Manager installieren")
        btn_virt_install.add_css_class("suggested-action")
        btn_virt_install.set_tooltip_text("Startet die Installation von Virt-Manager.\nDie Installation kann einen Moment dauern.")
        btn_virt_install.connect("clicked", self.on_virt_manager_password_ok)
        virt_manager_pass_box.append(btn_virt_install)

        btn_back_virt = Gtk.Button(label="Zurück")
        btn_back_virt.set_tooltip_text("Geht zurück zur Startseite.")
        btn_back_virt.connect("clicked", lambda x: self.stack.set_visible_child_name("welcome"))
        virt_manager_pass_box.append(btn_back_virt)

        self.stack.add_named(virt_manager_pass_box, "virt_manager_password")

        # ---- Snapshot-Hinweis ----
        snapshot_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        snapshot_box.set_halign(Gtk.Align.CENTER)
        snapshot_box.set_valign(Gtk.Align.CENTER)
        snapshot_box.set_margin_start(20)
        snapshot_box.set_margin_end(20)

        snapshot_label = Gtk.Label()
        snapshot_label.set_markup(
            "<big><b>📸 Wichtiger Hinweis zu Snapshots</b></big>\n\n"
            "Mit <b>Snapshots</b> kannst du den Zustand deiner virtuellen Maschine speichern\n"
            "und später wiederherstellen.\n\n"
            "⚠️ <b>Je nach VM-Konfiguration und verwendeter Snapshot-Technik</b>\n"
            "können Einschränkungen bestehen. Insbesondere interne Snapshots\n"
            "können bei UEFI-Konfigurationen problematisch sein.\n\n"
            "💡 <b>Tipp:</b>\n"
            "Wenn Snapshots für dich wichtig sind, verwende möglichst eine\n"
            "kompatible Standardkonfiguration und teste die Snapshot-Funktion\n"
            "nach dem Erstellen der VM einmal."
        )
        snapshot_label.set_justify(Gtk.Justification.LEFT)
        snapshot_label.set_wrap(True)
        snapshot_box.append(snapshot_label)

        btn_snapshot_ok = Gtk.Button(label="✅ OK, verstanden!")
        btn_snapshot_ok.add_css_class("suggested-action")
        btn_snapshot_ok.set_tooltip_text("Bestätigt, dass du den Hinweis gelesen hast und startet die Installation.")
        btn_snapshot_ok.connect("clicked", self.on_snapshot_ok_clicked)
        snapshot_box.append(btn_snapshot_ok)

        self.stack.add_named(snapshot_box, "snapshot_hint")

        # ---- Installation läuft ----
        install_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        install_box.set_halign(Gtk.Align.CENTER)
        install_box.set_valign(Gtk.Align.CENTER)

        self.install_status = Gtk.Label(label="Vorbereitung …")
        self.install_status.set_markup("<big>🔄 Vorbereitung …</big>")
        self.install_status.set_tooltip_text("Zeigt den aktuellen Installationsschritt an.")
        install_box.append(self.install_status)

        self.install_explanation = Gtk.Label()
        self.install_explanation.set_wrap(True)
        self.install_explanation.set_justify(Gtk.Justification.CENTER)
        self.install_explanation.set_markup("<i>Erklärung folgt …</i>")
        self.install_explanation.set_tooltip_text("Erklärung, was gerade passiert und warum dieser Schritt wichtig ist.")
        install_box.append(self.install_explanation)

        self.install_progress = Gtk.Label()
        self.install_progress.set_markup("<i>Schritt 0 von 0</i>")
        install_box.append(self.install_progress)

        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(50, 50)
        self.spinner.set_tooltip_text("Die Installation läuft …")
        install_box.append(self.spinner)

        btn_cancel = Gtk.Button(label="Installation verlassen")
        btn_cancel.add_css_class("destructive-action")
        btn_cancel.set_tooltip_text("Verlässt die Installation, sobald der aktuelle Schritt abgeschlossen ist.\nBereits gestartete Prozesse werden beendet.")
        btn_cancel.connect("clicked", self.on_cancel_clicked)
        install_box.append(btn_cancel)

        self.stack.add_named(install_box, "install")

        # ---- Virt-Manager Installation läuft ----
        virt_install_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        virt_install_box.set_halign(Gtk.Align.CENTER)
        virt_install_box.set_valign(Gtk.Align.CENTER)

        self.virt_install_status = Gtk.Label(label="Vorbereitung …")
        self.virt_install_status.set_markup("<big>🔧 Virt-Manager wird installiert …</big>")
        self.virt_install_status.set_tooltip_text("Zeigt den aktuellen Installationsschritt an.")
        virt_install_box.append(self.virt_install_status)

        self.virt_spinner = Gtk.Spinner()
        self.virt_spinner.set_size_request(50, 50)
        self.virt_spinner.set_tooltip_text("Die Installation von Virt-Manager läuft …")
        virt_install_box.append(self.virt_spinner)

        btn_virt_cancel = Gtk.Button(label="Installation verlassen")
        btn_virt_cancel.add_css_class("destructive-action")
        btn_virt_cancel.set_tooltip_text("Verlässt die Installation von Virt-Manager, sobald der aktuelle Schritt abgeschlossen ist.")
        btn_virt_cancel.connect("clicked", self.on_virt_cancel_clicked)
        virt_install_box.append(btn_virt_cancel)

        self.stack.add_named(virt_install_box, "virt_install")

        # ---- Deinstallation läuft ----
        uninstall_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        uninstall_box.set_halign(Gtk.Align.CENTER)
        uninstall_box.set_valign(Gtk.Align.CENTER)

        self.uninstall_status = Gtk.Label(label="Vorbereitung …")
        self.uninstall_status.set_markup("<big>🗑️ Vorbereitung …</big>")
        self.uninstall_status.set_tooltip_text("Zeigt den aktuellen Deinstallationsschritt an.")
        uninstall_box.append(self.uninstall_status)

        self.uninstall_spinner = Gtk.Spinner()
        self.uninstall_spinner.set_size_request(50, 50)
        self.uninstall_spinner.set_tooltip_text("Die Deinstallation läuft …")
        uninstall_box.append(self.uninstall_spinner)

        btn_uninstall_cancel = Gtk.Button(label="Deinstallation verlassen")
        btn_uninstall_cancel.add_css_class("destructive-action")
        btn_uninstall_cancel.set_tooltip_text("Verlässt die Deinstallation, sobald der aktuelle Schritt abgeschlossen ist.")
        btn_uninstall_cancel.connect("clicked", self.on_uninstall_cancel_clicked)
        uninstall_box.append(btn_uninstall_cancel)

        self.stack.add_named(uninstall_box, "uninstall")

        # ---- Fertig (Installation) ----
        finish_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        finish_box.set_halign(Gtk.Align.CENTER)
        finish_box.set_valign(Gtk.Align.CENTER)

        self.finish_label = Gtk.Label()
        self.finish_label.set_markup(
            "<big><b>✅ Installation erfolgreich!</b></big>\n\n"
            "GNOME Boxes und die zugehörigen Virtualisierungswerkzeuge sind jetzt installiert.\n\n"
            "🔔 <b>Wichtig:</b> Melde dich einmal ab und wieder an oder starte den Computer neu,\n"
            "damit die neuen Gruppenrechte aktiv werden.\n\n"
            "Danach kannst du GNOME Boxes über das Anwendungsmenü starten.\n\n"
            "📚 <b>Erste Schritte:</b>\n"
            "• Klicke auf 'Neue Box' und wähle ein Betriebssystem aus.\n"
            "• Teile Ordner über 'Geräte &amp; Freigaben'.\n"
            "• Finde Einstellungen unter dem Zahnrad-Symbol.\n\n"
            "📸 <b>Denk an den Snapshot-Hinweis:</b>\n"
            "Snapshots können je nach Konfiguration Einschränkungen haben."
        )
        self.finish_label.set_justify(Gtk.Justification.CENTER)
        self.finish_label.set_wrap(True)
        finish_box.append(self.finish_label)

        finish_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        finish_btn_box.set_halign(Gtk.Align.CENTER)

        btn_close = Gtk.Button(label="Schließen")
        btn_close.add_css_class("suggested-action")
        btn_close.set_tooltip_text("Schließt das GNOME-Boxes Tool.")
        btn_close.connect("clicked", lambda x: self.get_application().quit())
        finish_btn_box.append(btn_close)

        btn_virt = Gtk.Button(label="🔧 Virt-Manager installieren")
        btn_virt.add_css_class("pill")
        btn_virt.set_tooltip_text("Virt-Manager ist ein fortgeschrittenes Tool für VM-Einstellungen.\nEs bietet mehr Optionen als GNOME Boxes – perfekt, wenn du mehr Kontrolle möchtest.")
        btn_virt.connect("clicked", self.on_virt_manager_clicked)
        if is_virt_manager_installed():
            btn_virt.set_sensitive(False)
            btn_virt.set_tooltip_text("Virt-Manager ist bereits installiert.")
        finish_btn_box.append(btn_virt)

        finish_box.append(finish_btn_box)
        self.stack.add_named(finish_box, "finish")

        # ---- Fertig (Virt-Manager) ----
        virt_finish_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        virt_finish_box.set_halign(Gtk.Align.CENTER)
        virt_finish_box.set_valign(Gtk.Align.CENTER)

        self.virt_finish_label = Gtk.Label()
        self.virt_finish_label.set_markup(
            "<big><b>✅ Virt-Manager erfolgreich installiert!</b></big>\n\n"
            "Virt-Manager ist jetzt installiert.\n\n"
            "Du findest es im Anwendungsmenü oder startest es über das Terminal.\n\n"
            "💡 <b>Tipp:</b> Virt-Manager kann mit einer passenden libvirt-Verbindung\n"
            "deine GNOME-Boxes-VMs verwalten.\n\n"
            "Das Fenster kann jetzt geschlossen werden."
        )
        self.virt_finish_label.set_justify(Gtk.Justification.CENTER)
        self.virt_finish_label.set_wrap(True)
        virt_finish_box.append(self.virt_finish_label)

        btn_virt_close = Gtk.Button(label="Schließen")
        btn_virt_close.add_css_class("suggested-action")
        btn_virt_close.set_tooltip_text("Schließt das GNOME-Boxes Tool.")
        btn_virt_close.connect("clicked", lambda x: self.get_application().quit())
        virt_finish_box.append(btn_virt_close)

        self.stack.add_named(virt_finish_box, "virt_finish")

        # ---- Fertig (Deinstallation) ----
        uninstall_finish_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        uninstall_finish_box.set_halign(Gtk.Align.CENTER)
        uninstall_finish_box.set_valign(Gtk.Align.CENTER)

        self.uninstall_finish_label = Gtk.Label()
        self.uninstall_finish_label.set_markup(
            "<big><b>🗑️ Deinstallation erfolgreich!</b></big>\n\n"
            "GNOME Boxes und die zugehörigen Systempakete wurden entfernt.\n\n"
            "📁 <b>Deine virtuellen Maschinen wurden nicht gelöscht.</b>\n"
            "Standardmäßig befinden sie sich unter:\n"
            "   ~/.local/share/gnome-boxes/images/\n\n"
            "Je nach libvirt-Konfiguration können VM-Dateien auch\n"
            "an einem anderen Speicherort liegen.\n\n"
            "🧹 Nicht mehr benötigte Abhängigkeiten wurden automatisch entfernt.\n\n"
            "Das Fenster kann jetzt geschlossen werden."
        )
        self.uninstall_finish_label.set_justify(Gtk.Justification.CENTER)
        self.uninstall_finish_label.set_wrap(True)
        uninstall_finish_box.append(self.uninstall_finish_label)

        btn_uninstall_close = Gtk.Button(label="Schließen")
        btn_uninstall_close.add_css_class("suggested-action")
        btn_uninstall_close.set_tooltip_text("Schließt das GNOME-Boxes Tool.")
        btn_uninstall_close.connect("clicked", lambda x: self.get_application().quit())
        uninstall_finish_box.append(btn_uninstall_close)

        self.stack.add_named(uninstall_finish_box, "uninstall_finish")

        # ---- Fehler ----
        error_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        error_box.set_halign(Gtk.Align.CENTER)
        error_box.set_valign(Gtk.Align.CENTER)

        self.error_label = Gtk.Label()
        self.error_label.set_markup("<big><b>❌ Ein Fehler ist aufgetreten</b></big>")
        self.error_label.set_justify(Gtk.Justification.CENTER)
        self.error_label.set_wrap(True)
        error_box.append(self.error_label)

        btn_retry = Gtk.Button(label="Erneut versuchen")
        btn_retry.set_tooltip_text("Geht zurück zur Passwortseite, damit du es noch einmal versuchen kannst.")
        btn_retry.connect("clicked", self.on_retry_clicked)
        error_box.append(btn_retry)

        self.stack.add_named(error_box, "error")

        # ---- Diagnose-Seite ----
        diagnose_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        diagnose_box.set_halign(Gtk.Align.CENTER)
        diagnose_box.set_valign(Gtk.Align.CENTER)
        diagnose_box.set_margin_start(20)
        diagnose_box.set_margin_end(20)

        self.diagnose_status = Gtk.Label()
        self.diagnose_status.set_markup("<big>🔍 Diagnose läuft …</big>")
        self.diagnose_status.set_justify(Gtk.Justification.CENTER)
        self.diagnose_status.set_wrap(True)
        diagnose_box.append(self.diagnose_status)

        self.diagnose_spinner = Gtk.Spinner()
        self.diagnose_spinner.set_size_request(40, 40)
        diagnose_box.append(self.diagnose_spinner)

        # Container für die Ergebnisse (Liste)
        self.diagnose_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.diagnose_list_box.set_halign(Gtk.Align.FILL)
        diagnose_box.append(self.diagnose_list_box)

        btn_diagnose_back = Gtk.Button(label="Zurück")
        btn_diagnose_back.set_tooltip_text("Geht zurück zur Startseite.")
        btn_diagnose_back.connect("clicked", lambda x: self.stack.set_visible_child_name("welcome"))
        diagnose_box.append(btn_diagnose_back)

        self.stack.add_named(diagnose_box, "diagnose")

        # ---- Hilfe ----
        help_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        help_box.set_halign(Gtk.Align.CENTER)
        help_box.set_valign(Gtk.Align.CENTER)

        help_label = Gtk.Label()
        help_label.set_markup(
            "<big><b>❓ Hilfe &amp; FAQ</b></big>\n\n"
            "<b>1. VM ruckelt oder friert ein?</b>\n"
            "→ Deaktiviere die 3D-Beschleunigung in den VM-Einstellungen.\n"
            "   (Virt-Manager → Video → 3D-Acceleration aus)\n\n"
            "<b>2. VM startet nicht?</b>\n"
            "→ Stelle sicher, dass KVM aktiv ist: 'sudo kvm-ok'\n"
            "→ Prüfe, ob du in den Gruppen 'kvm' und 'libvirt' bist.\n\n"
            "<b>3. Ordnerfreigabe funktioniert nicht?</b>\n"
            "→ Installiere SPICE-Tools im Gast: 'sudo apt install spice-vdagent'\n"
            "→ Aktiviere die Ordnerfreigabe in den VM-Einstellungen.\n\n"
            "<b>4. Wo finde ich die VM-Dateien?</b>\n"
            "→ Standardmäßig unter ~/.local/share/gnome-boxes/images/\n\n"
            "<b>5. Wie installiere ich Virt-Manager?</b>\n"
            "→ Klicke nach der Installation auf den Button 'Virt-Manager installieren'.\n\n"
            "<b>6. Snapshots funktionieren nicht?</b>\n"
            "→ Snapshots können je nach VM-Konfiguration Einschränkungen haben.\n"
            "   Insbesondere interne Snapshots können bei UEFI problematisch sein.\n\n"
            "<b>7. Fehler beim Erstellen einer VM?</b>\n"
            "→ Fehlt qemu-utils? Das Paket wird bei der Installation mitinstalliert."
        )
        help_label.set_justify(Gtk.Justification.LEFT)
        help_label.set_wrap(True)
        help_box.append(help_label)

        btn_help_back = Gtk.Button(label="Zurück")
        btn_help_back.set_tooltip_text("Geht zurück zur Startseite.")
        btn_help_back.connect("clicked", lambda x: self.stack.set_visible_child_name("welcome"))
        help_box.append(btn_help_back)

        self.stack.add_named(help_box, "help")

        self.stack.set_visible_child_name("welcome")

        self.install_thread = None
        self.uninstall_thread = None
        self.virt_manager_thread = None
        self.diagnose_thread = None
        self.package_install_thread = None
        self.password = None

        self.update_buttons()

    # ==================== Button-Logik ====================

    def update_buttons(self):
        installed = is_gnome_boxes_installed()
        self.btn_start.set_sensitive(not installed)
        self.btn_uninstall.set_visible(installed)
        if installed:
            self.btn_start.set_tooltip_text("GNOME Boxes ist bereits installiert. Verwende den Deinstallations-Button.")
        else:
            self.btn_start.set_tooltip_text("Startet die Installation von GNOME Boxes und allen benötigten Komponenten.\nDu wirst nach deinem Passwort gefragt.")

    def clear_password_fields(self):
        self.password_entry.set_text("")
        self.uninstall_password_entry.set_text("")
        self.virt_password_entry.set_text("")

    # ==================== Diagnose ====================

    def on_diagnose_clicked(self, button):
        self.stack.set_visible_child_name("diagnose")
        self.diagnose_spinner.start()
        self.diagnose_status.set_markup("🔍 Sammle Systeminformationen …")

        # Leere alte Liste – GTK4-kompatibel
        child = self.diagnose_list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.diagnose_list_box.remove(child)
            child = next_child

        # Starte Diagnose-Thread
        self.diagnose_thread = threading.Thread(target=self._run_diagnose)
        self.diagnose_thread.daemon = True
        self.diagnose_thread.start()

    def _run_diagnose(self):
        results = run_diagnostic_checks()
        GLib.idle_add(self._display_diagnose_results, results)

    def _display_diagnose_results(self, results):
        self.diagnose_spinner.stop()
        self.diagnose_status.set_markup("📋 Abhängigkeiten-Check abgeschlossen")

        # Leere Liste – GTK4-kompatibel
        child = self.diagnose_list_box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.diagnose_list_box.remove(child)
            child = next_child

        # Für jedes Ergebnis eine Zeile bauen
        for item in results:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            row.set_halign(Gtk.Align.FILL)
            row.set_margin_bottom(5)

            # Status-Icon
            icon = Gtk.Label()
            if item['status'] == 'ok':
                icon.set_markup('✅')
            elif item['status'] == 'warning':
                icon.set_markup('⚠️')
            else:  # error
                icon.set_markup('❌')
            icon.set_width_chars(2)
            row.append(icon)

            # Name und Nachricht
            text = Gtk.Label()
            text.set_markup(f"<b>{item['name']}</b>  {item['message']}")
            text.set_halign(Gtk.Align.START)
            text.set_hexpand(True)
            text.set_wrap(True)
            row.append(text)

            # Install-Button, falls Paket fehlt und installierbar ist
            if item.get('package') and item['status'] in ('warning', 'error'):
                btn = Gtk.Button(label="Installieren")
                btn.add_css_class("suggested-action")
                btn.set_tooltip_text(f"Installiere {item['package']}")
                btn.connect("clicked", self._on_install_package_clicked, item['package'])
                row.append(btn)

            self.diagnose_list_box.append(row)

    def _on_install_package_clicked(self, button, package):
        """Wird aufgerufen, wenn der Benutzer ein Paket installieren möchte."""
        dialog = Adw.MessageDialog.new(
            self.get_application().get_active_window(),
            f"Passwort für Installation von {package}",
            "Für die Installation werden Administratorrechte benötigt."
        )
        entry = Gtk.Entry()
        entry.set_visibility(False)
        entry.set_placeholder_text("Passwort")
        entry.set_width_chars(20)
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        content_box.append(entry)
        dialog.set_extra_child(content_box)

        dialog.add_response("cancel", "Abbrechen")
        dialog.add_response("install", "Installieren")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)

        dialog.connect("response", self._on_install_dialog_response, package, entry)
        dialog.present()
        entry.grab_focus()

    def _on_install_dialog_response(self, dialog, response, package, entry):
        if response == "install":
            password = entry.get_text()
            if not password:
                return
            dialog.close()

            self.diagnose_status.set_markup(f"📦 Installiere {package} … bitte warten")
            self.diagnose_spinner.start()

            self.package_install_thread = PackageInstallThread(
                password=password,
                package=package,
                status_callback=self._on_package_install_status,
                finish_callback=self._on_package_install_finished,
                error_callback=self._on_package_install_error
            )
            self.package_install_thread.start()
        else:
            dialog.close()

    def _on_package_install_status(self, message):
        self.diagnose_status.set_markup(message)

    def _on_package_install_finished(self, success):
        self.diagnose_spinner.stop()
        if success:
            self.diagnose_status.set_markup("✅ Paket erfolgreich installiert – aktualisiere Anzeige …")
            self.on_diagnose_clicked(None)
        else:
            self.diagnose_status.set_markup("❌ Installation fehlgeschlagen – siehe Fehlermeldung")

    def _on_package_install_error(self, error_msg):
        self.diagnose_spinner.stop()
        self.diagnose_status.set_markup(f"❌ Fehler: {error_msg}")

    # ==================== Weitere Signal-Handler ====================

    def on_start_clicked(self, button):
        if is_gnome_boxes_installed():
            return
        self.stack.set_visible_child_name("snapshot_hint")

    def on_snapshot_ok_clicked(self, button):
        self.stack.set_visible_child_name("password")
        self.password_entry.grab_focus()
        self.password_error.set_visible(False)

    def on_password_ok(self, button):
        password = self.password_entry.get_text()
        if not password:
            return
        self.password = password
        self.password_error.set_visible(False)
        self.start_installation(password)

    def on_uninstall_clicked(self, button):
        self.stack.set_visible_child_name("uninstall_confirm")

    def on_uninstall_confirm_yes(self, button):
        self.stack.set_visible_child_name("uninstall_password")
        self.uninstall_password_entry.grab_focus()
        self.uninstall_password_error.set_visible(False)

    def on_uninstall_password_ok(self, button):
        password = self.uninstall_password_entry.get_text()
        if not password:
            return
        self.password = password
        self.uninstall_password_error.set_visible(False)
        self.start_uninstallation(password)

    def on_virt_manager_clicked(self, button):
        if is_virt_manager_installed():
            return
        self.stack.set_visible_child_name("virt_manager_hint")

    def on_virt_hint_ok_clicked(self, button):
        self.stack.set_visible_child_name("virt_manager_password")
        self.virt_password_entry.grab_focus()
        self.virt_password_error.set_visible(False)

    def on_virt_manager_password_ok(self, button):
        password = self.virt_password_entry.get_text()
        if not password:
            return
        self.password = password
        self.virt_password_error.set_visible(False)
        self.start_virt_manager_installation(password)

    def on_uninstall_cancel_clicked(self, button):
        if self.uninstall_thread and self.uninstall_thread.is_alive():
            self.uninstall_thread.cancel()
            self.uninstall_thread.join(timeout=2)
        self.uninstall_spinner.stop()
        self.stack.set_visible_child_name("welcome")
        self.clear_password_fields()

    def on_virt_cancel_clicked(self, button):
        if self.virt_manager_thread and self.virt_manager_thread.is_alive():
            self.virt_manager_thread.cancel()
            self.virt_manager_thread.join(timeout=2)
        self.virt_spinner.stop()
        self.stack.set_visible_child_name("welcome")
        self.clear_password_fields()

    def start_installation(self, password):
        self.password = password
        self.stack.set_visible_child_name("install")
        self.spinner.start()
        self.install_status.set_label("Starte Installation …")
        self.install_explanation.set_markup("<i>Vorbereitung …</i>")
        self.install_progress.set_markup("<i>Schritt 0 von 0</i>")
        self.install_thread = InstallerThread(
            password=password,
            status_callback=self.update_status,
            error_callback=self.show_error,
            finish_callback=self.finish_installation,
            step_explanation_callback=self.update_explanation,
            progress_callback=self.update_progress
        )
        self.install_thread.start()

    def start_uninstallation(self, password):
        self.password = password
        self.stack.set_visible_child_name("uninstall")
        self.uninstall_spinner.start()
        self.uninstall_status.set_markup("🗑️ Deinstallation wird vorbereitet …")
        self.uninstall_thread = UninstallThread(
            password=password,
            status_callback=self.update_uninstall_status,
            error_callback=self.show_error,
            finish_callback=self.finish_uninstallation
        )
        self.uninstall_thread.start()

    def start_virt_manager_installation(self, password):
        self.password = password
        self.stack.set_visible_child_name("virt_install")
        self.virt_spinner.start()
        self.virt_install_status.set_markup("🔧 Virt-Manager wird installiert …")
        self.virt_manager_thread = VirtManagerInstallThread(
            password=password,
            status_callback=self.update_virt_install_status,
            error_callback=self.show_error,
            finish_callback=self.finish_virt_installation
        )
        self.virt_manager_thread.start()

    def on_cancel_clicked(self, button):
        if self.install_thread and self.install_thread.is_alive():
            self.install_thread.cancel()
            self.install_thread.join(timeout=2)
        self.spinner.stop()
        self.stack.set_visible_child_name("welcome")
        self.clear_password_fields()

    def on_retry_clicked(self, button):
        self.stack.set_visible_child_name("password")
        self.password_entry.set_text("")
        self.password_entry.grab_focus()
        self.password_error.set_visible(False)
        self.clear_password_fields()

    def show_help(self, button, context):
        self.stack.set_visible_child_name("help")

    # ==================== Callbacks für Threads ====================

    def update_status(self, text):
        self.install_status.set_markup(f"<big>{text}</big>")

    def update_explanation(self, text):
        self.install_explanation.set_markup(f"<i>{text}</i>")

    def update_progress(self, current, total):
        self.install_progress.set_markup(f"<i>Schritt {current} von {total}</i>")

    def update_uninstall_status(self, text):
        self.uninstall_status.set_markup(f"<big>{text}</big>")

    def update_virt_install_status(self, text):
        self.virt_install_status.set_markup(f"<big>{text}</big>")

    def show_error(self, message):
        self.error_label.set_markup(f"<big><b>❌ Fehler</b></big>\n\n{message}")
        self.stack.set_visible_child_name("error")
        self.clear_password_fields()

    def finish_installation(self, success):
        self.spinner.stop()
        self.clear_password_fields()
        if success:
            self.stack.set_visible_child_name("finish")
            self.update_buttons()
        else:
            self.stack.set_visible_child_name("welcome")
        self.password = None

    def finish_uninstallation(self, success):
        self.uninstall_spinner.stop()
        self.clear_password_fields()
        if success:
            self.stack.set_visible_child_name("uninstall_finish")
            self.update_buttons()
        else:
            self.stack.set_visible_child_name("welcome")
        self.password = None

    def finish_virt_installation(self, success):
        self.virt_spinner.stop()
        self.clear_password_fields()
        if success:
            self.stack.set_visible_child_name("virt_finish")
        else:
            self.stack.set_visible_child_name("welcome")
        self.password = None

# ====================== Anwendungsstart ======================

class ToolApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id='org.gnome.boxes.tool')
        self.connect('activate', self.on_activate)

    def on_activate(self, app):
        win = ToolWindow(app)
        win.present()

def main():
    try:
        app = ToolApp()
        return app.run(sys.argv)
    except Exception as e:
        print("Fehler beim Starten der grafischen Oberfläche:", e)
        print("Bitte installiere: python3-gi python3-gi-cairo gir1.2-adw-1")
        return 1

if __name__ == '__main__':
    sys.exit(main())
