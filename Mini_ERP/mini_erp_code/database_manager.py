from mini_erp_code.customer import Customer
from mini_erp_code.item import Item
from mini_erp_code.sales_order import SalesOrder
from mini_erp_code.system_user import SystemUser


class DatabaseManager:


    def __init__(self):
        self.customer_db = "mini_erp_code/database/customers.csv"
        self.user_db = "mini_erp_code/database/users.csv"
        self.item_db = "mini_erp_code/database/items.csv"
        self.sales_order_db = "mini_erp_code/database/sales_orders.csv"

    ##############################################################
    # Customer related methods
    def load_customers(self):
        customers = []
        with open(self.customer_db, "r") as file:
            """
            keep getting an error from testing, because I have 3 customer objects (should be 2.
            Fixed with skipping the first line (headers).
            Source: https://stackoverflow.com/questions/14674275/skip-first-linefield-in-loop-using-csv-file
            """
            next(file)
            for line in file:
                line = line.strip()
                customer_id, name, city, address, phone, email = line.split(",")
                customers.append(Customer(customer_id, name, city, address, phone, email))

        return customers

# Source for writing new information to a csv: https://stackoverflow.com/questions/2363731/how-to-append-a-new-row-to-an-old-csv-file-in-python
    def save_new_customer(self, new_customer_info):
        new_line = ','.join(new_customer_info)

        with open(self.customer_db, "a") as file:
            file.write("\n")
            file.write(new_line)

        return "New customer created successfully!"

##############################################################
    #System User related methods
    def load_users(self):
        users = []
        with open(self.user_db, "r") as file:
            next(file)
            for line in file:
                line = line.strip()
                user_id, name, password, access_level, = line.split(",")
                users.append(SystemUser(user_id, name, password, access_level))

        return users

    # Source for writing new information to a csv: https://stackoverflow.com/questions/2363731/how-to-append-a-new-row-to-an-old-csv-file-in-python
    def save_new_user(self, new_user_info):
        new_line = ','.join(new_user_info)

        with open(self.customer_db, "a") as file:
            file.write("\n")
            file.write(new_line)

        return "New user created successfully!"

    ##############################################################
    # Item related methods
    def load_items(self):
        items = []
        with open(self.item_db, "r") as file:
            next(file)
            for line in file:
                line = line.strip()
                item_id, name, price, quantity, cost = line.split(",")
                items.append(Item(item_id, name, price, quantity, cost))

        return items


# Source for writing new information to a csv: https://stackoverflow.com/questions/2363731/how-to-append-a-new-row-to-an-old-csv-file-in-python
    def save_new_item(self, new_item_info):
        new_line = ','.join(new_item_info)

        with open(self.customer_db, "a") as file:
            file.write("\n")
            file.write(new_line)

        return "New Item created successfully!"
    ##############################################################
    # Sales order related methods
    def load_sales_orders(self):
        sales_orders = []
        with open(self.sales_order_db, "r") as file:
            next(file)
            for line in file:
                line = line.strip()
                order_id, customer, creator = line.split(",")
                sales_orders.append(SalesOrder(order_id, customer, creator))

        return sales_orders


    # Source for writing new information to a csv: https://stackoverflow.com/questions/2363731/how-to-append-a-new-row-to-an-old-csv-file-in-python
    def save_new_sales_order(self, new_order_info):
        new_line = ','.join(new_order_info)

        with open(self.customer_db, "a") as file:
            file.write("\n")
            file.write(new_line)

        return "New sales order created successfully!"






















##################### Maybe these later
    # Methods for retrieving info from the database.
    def get_log_in(self):
        pass
    def get_user_by_id(self, user_id):
        pass
    def get_customer_by_id(self, customer_id):
        pass
    def get_item_by_id(self, item_id):
        pass

    # Methods for adding into the database.
    def add_user(self, user_id):
        pass
    def add_customer(self, customer_id):
        pass
    def add_item(self, item_id):
        pass
    def add_sales_order(self, sales_order_id):
        pass

    # Methods for removing from the database.
    def remove_user(self, user_id):
        pass
    def remove_customer(self, customer_id):
        pass
    def remove_item(self, item_id):
        pass
    def remove_sales_order(self, sales_order_id):
        pass


    # Methods for updating the information in the database
    def update_user(self, update, user_id):
        pass
    def update_customer(self, update, user_id):
        pass
    def update_item(self, update, user_id):
        pass
    def update_sales_order(self, update, user_id):
        pass
