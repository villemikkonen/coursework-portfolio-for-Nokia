from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton


class SettingsView(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.manage_settings_button = QPushButton("Manage settings")

        self.layout().addWidget(self.manage_settings_button)