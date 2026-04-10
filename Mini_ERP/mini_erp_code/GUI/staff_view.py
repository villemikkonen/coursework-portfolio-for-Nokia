from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QStackedLayout, QStackedWidget, QFormLayout, QLineEdit)




class StaffView(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.stackedWidget = QStackedWidget()
        self.main_view = StaffViewMainPage()
        self.add_new_user_view = AddNewUserPage()

        self.stackedWidget.addWidget(self.main_view)
        self.stackedWidget.addWidget(self.add_new_user_view)

        self.layout().addWidget(self.stackedWidget)

        self.main_view.add_new_user_button.clicked.connect(self.new_sales_order)
        self.add_new_user_view.go_back_button.clicked.connect(self.back_to_main)

    def new_sales_order(self):
        self.stackedWidget.setCurrentIndex(1)

    def back_to_main(self):
        self.stackedWidget.setCurrentIndex(0)

    def confirm_new_sales_order(self):
        pass    #TODO: Implement functionality



class StaffViewMainPage(QWidget):

    def __init__(self):
        super().__init__()
        self.setLayout(QHBoxLayout())

        self.add_new_user_button = QPushButton("Create New System User")
        self.manage_staff_button = QPushButton("Manage Users")
        self.examine_staff_button = QPushButton("Examine User info")

        self.layout().addWidget(self.add_new_user_button)
        self.layout().addWidget(self.manage_staff_button)
        self.layout().addWidget(self.examine_staff_button)



class AddNewUserPage(QWidget):

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout()
        form_layout = QFormLayout()
        navigation_layout = QHBoxLayout()

        self.add_new_user_button = QPushButton("Confirm")
        self.go_back_button = QPushButton("Go Back")

        form_layout.addRow("User ID", QLineEdit(self))
        form_layout.addRow("Name", QLineEdit(self))
        form_layout.addRow("Password", QLineEdit(self))
        form_layout.addRow("confirm Password", QLineEdit(self))

        navigation_layout.addWidget(self.add_new_user_button)
        navigation_layout.addWidget(self.go_back_button)

        main_layout.addLayout(form_layout)
        main_layout.addLayout(navigation_layout)

        self.setLayout(main_layout)