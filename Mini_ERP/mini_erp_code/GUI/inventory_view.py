from PyQt6.QtWidgets import (QWidget, QPushButton, QHBoxLayout, QVBoxLayout,
                             QStackedWidget, QFormLayout, QLineEdit)

# Architecture source / inspiration: https://stackoverflow.com/questions/65959355/class-for-each-qstackedwidget-page
# AND Course material round 5 "PyQt windows" etc.
class InventoryView(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.stackedWidget = QStackedWidget()
        self.main_view = InventoryViewMainPage()
        self.new_item_view = AddNewItemPage()

        self.stackedWidget.addWidget(self.main_view)
        self.stackedWidget.addWidget(self.new_item_view)

        self.layout().addWidget(self.stackedWidget)

        self.main_view.add_new_item_button.clicked.connect(self.add_new_item_clicked)
        self.new_item_view.go_back_button.clicked.connect(self.back_to_main)


    def add_new_item_clicked(self):
        self.stackedWidget.setCurrentIndex(1)

    def back_to_main(self):
        self.stackedWidget.setCurrentIndex(0)

    def confirm_new_item(self):
        pass        #TODO: Implement functionality


class InventoryViewMainPage(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.add_new_item_button = QPushButton("Add New Item")
        self.manage_inventory_button = QPushButton("Manage Inventory Items")
        self.examine_inventory_button = QPushButton("Examine Inventory")

        self.layout().addWidget(self.add_new_item_button)
        self.layout().addWidget(self.manage_inventory_button)
        self.layout().addWidget(self.examine_inventory_button)





class AddNewItemPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        navigation_layout = QHBoxLayout()

        self.add_new_item_button = QPushButton("Confirm")
        self.go_back_button = QPushButton("Go Back")

        form_layout.addRow("Item ID", QLineEdit(self))
        form_layout.addRow("Name", QLineEdit(self))
        form_layout.addRow("Price", QLineEdit(self))
        form_layout.addRow("Quantity", QLineEdit(self))
        form_layout.addRow("Cost", QLineEdit(self))

        navigation_layout.addWidget(self.add_new_item_button)
        navigation_layout.addWidget(self.go_back_button)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(navigation_layout)

        self.setLayout(main_layout)