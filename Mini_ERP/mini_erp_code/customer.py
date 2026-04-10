class Customer:


    def __init__(self, customer_id, name, city, address, phone, email):
        self.customer_id = customer_id
        self.name = name            #Basic attributes
        self.city = city
        self.address = address
        self.phone = phone
        self.email = email
        self.orders = []            # For keeping track of orders that a customer has. Empty at first.


    # Method for retrieving customer's info.
    def get_info(self):
        return [self.customer_id, self.name, self.city, self.address, self.phone, self.email]


    # Methods for updating customer's orders.
    def add_sales_order(self, order):
        self.orders.append(order)
    def remove_sales_order(self, order):
        self.orders.remove(order)
