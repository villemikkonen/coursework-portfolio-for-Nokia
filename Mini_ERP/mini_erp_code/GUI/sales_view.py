from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFormLayout,
QLineEdit, QStackedLayout, QStackedWidget)


class SalesView(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.stackedWidget = QStackedWidget()
        self.main_view = SalesViewMainPage()
        self.add_new_sales_order_view = AddNewSalesOrderPage()

        self.stackedWidget.addWidget(self.main_view)
        self.stackedWidget.addWidget(self.add_new_sales_order_view)

        self.layout().addWidget(self.stackedWidget)

        self.main_view.create_new_sales_order_button.clicked.connect(self.new_sales_order)
        self.add_new_sales_order_view.go_back_button.clicked.connect(self.back_to_main)

    def new_sales_order(self):
        self.stackedWidget.setCurrentIndex(1)

    def back_to_main(self):
        self.stackedWidget.setCurrentIndex(0)

    def confirm_new_sales_order(self):
        pass    #TODO: Implement functionality



class SalesViewMainPage(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.create_new_sales_order_button = QPushButton("Add New Sales Order")
        self.manage_sales_orders_button = QPushButton("Manage Sales Orders")
        self.examine_sales_orders_button = QPushButton("Examine Sales Orders")

        self.layout().addWidget(self.create_new_sales_order_button)
        self.layout().addWidget(self.manage_sales_orders_button)
        self.layout().addWidget(self.examine_sales_orders_button)


class AddNewSalesOrderPage(QWidget):

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        navigation_layout = QHBoxLayout()

        self.add_new_sales_order_button = QPushButton("Confirm")
        self.go_back_button = QPushButton("Go Back")

        form_layout.addRow("Order ID", QLineEdit(self))
        form_layout.addRow("Customer ID", QLineEdit(self))
        form_layout.addRow("User ID", QLineEdit(self))

        navigation_layout.addWidget(self.add_new_sales_order_button)
        navigation_layout.addWidget(self.go_back_button)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(navigation_layout)

        self.setLayout(main_layout)