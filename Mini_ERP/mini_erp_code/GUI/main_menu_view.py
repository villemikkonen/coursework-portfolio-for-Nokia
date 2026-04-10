from PyQt6 import QtCore, QtGui
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QHBoxLayout, QVBoxLayout, QLabel, \
    QGridLayout, QMainWindow, QTabWidget

from mini_erp_code.GUI.customers_view import CustomersView
from mini_erp_code.GUI.inventory_view import InventoryView
from mini_erp_code.GUI.sales_view import SalesView
from mini_erp_code.GUI.settings_view import SettingsView
from mini_erp_code.GUI.staff_view import StaffView


class MainMenuView(QWidget):

    """Heavily inspired by round 5 of course materials.
       Code structure source: https://www.pythontutorial.net/pyqt/pyqt-qtabwidget/ """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mini-ERP | Main Menu")
        self.setGeometry(20, 20, 700, 350)

        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        tab = QTabWidget(self)

        #Adding Views
        customers_view = CustomersView()
        sales_view = SalesView()
        inventory_view = InventoryView()
        staff_view = StaffView()
        settings_view = SettingsView()

        tab.addTab(customers_view, "Customers")
        tab.addTab(sales_view, "Sales")
        tab.addTab(inventory_view, "Inventory")
        tab.addTab(staff_view, "Staff")
        tab.addTab(settings_view, "Settings")

        main_layout.addWidget(tab)

        self.show()