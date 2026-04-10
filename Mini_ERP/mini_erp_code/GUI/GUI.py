import sys

from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, \
    QGridLayout, QMainWindow

from mini_erp_code.GUI.main_menu_view import MainMenuView


class GUI(QWidget):

    def __init__(self):
        super().__init__()

        self.main_menu_view = MainMenuView()




if __name__ == "__main__":              # For quickly testing what the gui is looking like atm.
    app = QApplication(sys.argv)
    main_menu_view = MainMenuView()
    sys.exit(app.exec())