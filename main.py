"""pySIMIO application entry point."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication, QMessageBox

from gui.main_window import MainWindow
from persistence.project_store import ProjectStore

APP_NAME = "pySIMIO"
ORGANIZATION_NAME = "pySIMIO"


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _startup_store(arguments: list[str]) -> ProjectStore:
    store = ProjectStore()
    if len(arguments) < 2:
        return store
    candidate = Path(arguments[1]).expanduser()
    try:
        store.open(candidate)
    except Exception as exc:
        QMessageBox.critical(None, "Unable to Open Project", f"pySIMIO could not open:\n{candidate}\n\n{exc}")
        store.new()
    return store


def main() -> int:
    configure_logging()
    QCoreApplication.setApplicationName(APP_NAME)
    QCoreApplication.setOrganizationName(ORGANIZATION_NAME)
    app = QApplication(sys.argv)
    app.setApplicationDisplayName(APP_NAME)
    store = _startup_store(sys.argv)
    window = MainWindow(store=store, plc=None)
    window.resize(1200, 760)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
