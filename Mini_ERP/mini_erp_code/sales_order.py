import datetime

from mini_erp_code.item import Item


class SalesOrder:


    def __init__(self, order_id, customer_id, user_id):
        self.order_id = order_id
        self.customer = customer_id                    # Basic info attributes
        self.creator = user_id
        #self.delivery_address = customer.address TODO Make work with either objects OR some other way(?)
        self.date = datetime.datetime.now()         # For timestamping. TODO Check with TA if OK.
        self.items = []                             # For tracking items included. Can be empty.


        # Methods for updating content.
    def add_item(self, item, quantity):
        self.items.append((item, quantity))
    def remove_item(self, item, quantity):
        self.items.remove((item, quantity))


        # Methods for changing info.
    def change_customer(self, customer):
        self.customer = customer
    def change_creator(self, creator):
        self.creator = creator
    def change_delivery_address(self, new_address):     # Assuming every address given is valid.
        self.delivery_address = new_address