class Item:


    def __init__(self, item_id, name, price, quantity, cost = 0):
        self.item_id = item_id
        self.name = name
        self.price = price
        self.quantity = quantity
        self.cost = cost               # Cost = 0 until changed to something


    # Methods for controlling stock levels
    def add_stock(self, increase):
        self.quantity += increase

    def remove_stock(self, reduction):
        self.quantity -= reduction
