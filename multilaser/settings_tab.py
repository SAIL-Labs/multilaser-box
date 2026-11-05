"""
Settings Tab Widget

Collects the app's stored configuration in one place:

- Power meter connection and role assignment (the group boxes are
  re-parented here from the Power Meters tab)
- Known power meters and their friendly names (e.g. matching the labels
  on the hardware), keyed by meter serial number
- Auto-connect to the last-used meters at startup (skips scan/connect)
- Default save folder for measurement logs (e.g. the OneDrive
  "Lantern Data" folder, whose location varies per computer)
- Airtable access token management

Author: Multi-Laser Box Project
Date: 2026-08-20
"""

import datetime
import logging
import os
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMessageBox,
)
from PyQt6.QtCore import QSettings, Qt

from multilaser.power_meter_tab import PowerMeterTab

logger = logging.getLogger(__name__)


class SettingsTab(QWidget):
    """Settings tab hosting connection, startup, file and Airtable options"""

    def __init__(
        self, settings: QSettings, power_meter_tab: PowerMeterTab, parent=None
    ):
        super().__init__(parent)
        self.settings = settings
        self.pm_tab = power_meter_tab
        self.init_ui()

    def init_ui(self):
        """Initialize the user interface"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # === Power meter connection & roles (re-parented from pm tab) ===
        layout.addWidget(self.pm_tab.connection_group)
        layout.addWidget(self.pm_tab.role_group)

        # === Known power meters / friendly names ===
        layout.addWidget(self._create_known_meters_group())

        # === Startup ===
        startup_group = QGroupBox("Startup")
        startup_layout = QVBoxLayout()

        self.auto_connect_check = QCheckBox(
            "Automatically connect to the last-used power meters at startup"
        )
        self.auto_connect_check.setToolTip(
            "Skips Scan/Connect: on launch the app connects directly to\n"
            "the meters used last time (by their saved VISA resources)\n"
            "and restores their Reference/Target roles.\n"
            "Turn off when the hardware setup changes."
        )
        self.auto_connect_check.setChecked(
            self.settings.value(
                "power_meter/auto_connect", defaultValue=True, type=bool
            )
        )
        self.auto_connect_check.toggled.connect(
            lambda on: self.settings.setValue("power_meter/auto_connect", on)
        )
        startup_layout.addWidget(self.auto_connect_check)

        startup_group.setLayout(startup_layout)
        layout.addWidget(startup_group)

        # === Measurement files ===
        files_group = QGroupBox("Measurement Files")
        files_layout = QHBoxLayout()

        files_layout.addWidget(QLabel("Default save folder:"))
        self.folder_label = QLabel()
        self.folder_label.setStyleSheet("color: #2c3e50;")
        files_layout.addWidget(self.folder_label, stretch=1)

        choose_folder_btn = QPushButton("Choose…")
        choose_folder_btn.setToolTip(
            "Folder where log file dialogs start\n"
            "(e.g. the Lantern Data folder on OneDrive)"
        )
        choose_folder_btn.clicked.connect(self.choose_default_log_dir)
        files_layout.addWidget(choose_folder_btn)

        clear_folder_btn = QPushButton("Clear")
        clear_folder_btn.setToolTip("Fall back to the last-used folder")
        clear_folder_btn.clicked.connect(self.clear_default_log_dir)
        files_layout.addWidget(clear_folder_btn)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        self._refresh_folder_label()

        # === Airtable ===
        airtable_group = QGroupBox("Airtable (SAIL Lantern Manufacture)")
        airtable_layout = QHBoxLayout()

        airtable_layout.addWidget(QLabel("Access token:"))
        self.airtable_status_label = QLabel()
        airtable_layout.addWidget(self.airtable_status_label, stretch=1)

        set_token_btn = QPushButton("Set Token…")
        set_token_btn.setToolTip(
            "Store an Airtable personal access token (PAT) scoped to\n"
            "data.records:read/write on the Lantern Manufacture base"
        )
        set_token_btn.clicked.connect(self.set_airtable_token)
        airtable_layout.addWidget(set_token_btn)

        forget_token_btn = QPushButton("Forget Token")
        forget_token_btn.clicked.connect(self.forget_airtable_token)
        airtable_layout.addWidget(forget_token_btn)

        airtable_group.setLayout(airtable_layout)
        layout.addWidget(airtable_group)
        self._refresh_airtable_status()

        layout.addStretch()
        self.setLayout(layout)

    # === Known power meters ===

    COLUMNS = ["Name", "Serial", "Model", "Status", "Sensor", "Last seen"]

    def _create_known_meters_group(self) -> QGroupBox:
        group = QGroupBox("Known Power Meters")
        group.setToolTip(
            "Meters this computer has connected to, by serial number.\n"
            "Double-click a Name to set a friendly name (e.g. the label on\n"
            "the meter). Names appear in scans, role menus and displays."
        )
        v = QVBoxLayout()
        self.meters_table = QTableWidget(0, len(self.COLUMNS))
        self.meters_table.setHorizontalHeaderLabels(self.COLUMNS)
        header = self.meters_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.meters_table.verticalHeader().setVisible(False)
        self.meters_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.meters_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.meters_table.setMaximumHeight(160)
        self.meters_table.itemChanged.connect(self._on_meter_item_changed)
        v.addWidget(self.meters_table)

        row = QHBoxLayout()
        row.addWidget(QLabel(
            "Tip: connect one meter at a time, or cover a sensor and watch which "
            "reading drops, to match a serial to its label."
        ))
        row.addStretch()
        remove_btn = QPushButton("Forget Selected")
        remove_btn.setToolTip("Remove the selected meter and its name from this list")
        remove_btn.clicked.connect(self.forget_selected_meter)
        row.addWidget(remove_btn)
        v.addLayout(row)
        group.setLayout(v)

        self.pm_tab.known_meters_changed.connect(self.refresh_known_meters)
        self.refresh_known_meters()
        return group

    def refresh_known_meters(self):
        """Rebuild the known-meters table from the registry."""
        devices = self.pm_tab.registry.devices()
        roles = self.pm_tab.meter_roles()
        self.meters_table.blockSignals(True)
        self.meters_table.setRowCount(0)
        for serial in sorted(devices, key=lambda s: (s not in roles, s)):
            info = devices[serial]
            r = self.meters_table.rowCount()
            self.meters_table.insertRow(r)
            last_seen = info.get("last_seen")
            seen_text = (
                datetime.datetime.fromtimestamp(last_seen).strftime("%Y-%m-%d %H:%M")
                if last_seen else ""
            )
            values = [
                info.get("name", ""),
                serial,
                info.get("model", ""),
                roles.get(serial, ""),
                info.get("sensor", ""),
                seen_text,
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c != 0:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if c == 1:
                    item.setToolTip(f"Last resource: {info.get('resource', '')}")
                item.setData(Qt.ItemDataRole.UserRole, serial)
                self.meters_table.setItem(r, c, item)
        self.meters_table.blockSignals(False)

    def _on_meter_item_changed(self, item: QTableWidgetItem):
        if item.column() != 0:
            return
        serial = item.data(Qt.ItemDataRole.UserRole)
        self.pm_tab.registry.set_name(serial, item.text())
        self.pm_tab.refresh_meter_names()

    def forget_selected_meter(self):
        rows = {i.row() for i in self.meters_table.selectedItems()}
        if not rows:
            return
        serials = [self.meters_table.item(r, 1).text() for r in sorted(rows)]
        reply = QMessageBox.question(
            self, "Forget Meters",
            "Forget " + ", ".join(serials) + " and their names?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        for serial in serials:
            self.pm_tab.registry.remove(serial)
        self.refresh_known_meters()
        self.pm_tab.refresh_meter_names()

    # === Measurement files ===

    def _refresh_folder_label(self):
        default_dir = self.pm_tab._default_log_dir()
        if default_dir:
            self.folder_label.setText(default_dir)
            self.folder_label.setToolTip(default_dir)
        else:
            self.folder_label.setText(
                "Not set — dialogs open in the last-used folder"
            )
            self.folder_label.setToolTip("")

    def choose_default_log_dir(self):
        """Pick the default save folder for measurement logs"""
        current = self.pm_tab._default_log_dir()
        path = QFileDialog.getExistingDirectory(
            self,
            "Default Log Folder",
            current or self.pm_tab._log_start_dir(),
        )
        if not path:
            return
        self.settings.setValue("power_meter/default_log_dir", path)
        self._refresh_folder_label()

    def clear_default_log_dir(self):
        """Unset the default save folder"""
        self.settings.setValue("power_meter/default_log_dir", "")
        self._refresh_folder_label()

    # === Airtable ===

    def _refresh_airtable_status(self):
        if os.environ.get("MULTILASER_AIRTABLE_PAT", "").strip():
            text = "Set via MULTILASER_AIRTABLE_PAT environment variable"
        elif self.settings.value("airtable/pat", defaultValue="", type=str):
            text = "Token stored"
        else:
            text = "Not set — you will be asked when needed"
        self.airtable_status_label.setText(text)

    def set_airtable_token(self):
        """Prompt for and store an Airtable PAT"""
        pat, ok = QInputDialog.getText(
            self,
            "Airtable Access Token",
            "Paste an Airtable personal access token (PAT) scoped to\n"
            "data.records:read/write on the Lantern Manufacture base:",
            QLineEdit.EchoMode.Password,
        )
        pat = pat.strip() if ok else ""
        if not pat:
            return
        self.settings.setValue("airtable/pat", pat)
        self._refresh_airtable_status()

    def forget_airtable_token(self):
        """Remove the stored Airtable PAT (env var override unaffected)"""
        self.settings.setValue("airtable/pat", "")
        # A cached device list may belong to another base/token
        self.settings.setValue("airtable/device_serials", "")
        self.settings.setValue("airtable/device_serials_time", 0.0)
        self._refresh_airtable_status()
