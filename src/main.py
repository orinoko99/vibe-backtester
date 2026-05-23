"""
Точка входа в приложение Vibe Backtester.
"""

import sys

from pyqtgraph.Qt import QtWidgets

from src.ui.app import ГлавноеОкно


def main() -> None:
    """
    Запускает главное окно приложения.
    """
    приложение = QtWidgets.QApplication(sys.argv)
    приложение.setApplicationName("Vibe Backtester")
    приложение.setOrganizationName("Orinoko")

    окно = ГлавноеОкно()
    окно.show()

    sys.exit(приложение.exec())


if __name__ == "__main__":
    main()
