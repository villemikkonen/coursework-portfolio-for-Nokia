from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QStackedLayout, QStackedWidget, QFormLayout, QLineEdit)

from mini_erp_code.database_manager import DatabaseManager


class CustomersView(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.stackedWidget = QStackedWidget()
        self.main_view = CustomersViewMainPage()
        self.add_new_customer_view = AddNewCustomerPage()

        self.stackedWidget.addWidget(self.main_view)
        self.stackedWidget.addWidget(self.add_new_customer_view)

        self.layout().addWidget(self.stackedWidget)

        #navigating between views
        self.main_view.add_new_customer_button.clicked.connect(self.new_sales_order)
        self.add_new_customer_view.go_back_button.clicked.connect(self.back_to_main)

        #Confirming changes
        self.add_new_customer_view.add_new_customer_button.clicked.connect(self.confirm_new_customer)

    def new_sales_order(self):
        self.stackedWidget.setCurrentIndex(1)

    def back_to_main(self):
        self.stackedWidget.setCurrentIndex(0)


# Source for architecture inspiration: https://stackoverflow.com/questions/3016974/how-to-get-text-in-qlineedit-when-qpushbutton-is-pressed-in-a-string
    def confirm_new_customer(self):
        id_input = AddNewCustomerPage().id_input.text()
        name_input = AddNewCustomerPage().name_input.text()
        city_input = AddNewCustomerPage().city_input.text()
        address_input = AddNewCustomerPage().address_input.text()
        phone_input = AddNewCustomerPage().phone_input.text()
        email_input = AddNewCustomerPage().email_input.text()

        new_customer_info = [id_input, name_input, city_input, address_input, phone_input, email_input]



class CustomersViewMainPage(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.add_new_customer_button = QPushButton("Add New Customer")
        self.manage_customers_button = QPushButton("Manage Customer's Information")
        self.examine_customer_button = QPushButton("Examine Customers")

        self.layout().addWidget(self.add_new_customer_button)
        self.layout().addWidget(self.manage_customers_button)
        self.layout().addWidget(self.examine_customer_button)



class AddNewCustomerPage(QWidget):
    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        navigation_layout = QHBoxLayout()

        self.add_new_customer_button = QPushButton("Confirm")
        self.go_back_button = QPushButton("Go Back")

        #creating named variables so that I can later extract the input from QLineEdits in confirm_new_customer
        self.id_input = QLineEdit(self)
        self.name_input = QLineEdit(self)
        self.city_input = QLineEdit(self)
        self.address_input = QLineEdit(self)
        self.phone_input = QLineEdit(self)
        self.email_input = QLineEdit(self)


        form_layout.addRow("Customer ID", self.id_input)
        form_layout.addRow("Name", self.name_input)
        form_layout.addRow("City", self.city_input)
        form_layout.addRow("Address", self.address_input)
        form_layout.addRow("Phone", self.phone_input)
        form_layout.addRow("E-Mail", self.email_input)

        navigation_layout.addWidget(self.add_new_customer_button)
        navigation_layout.addWidget(self.go_back_button)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(navigation_layout)

        self.setLayout(main_layout)