import unittest

from mini_erp_code.database import *
from mini_erp_code.database_manager import DatabaseManager
from mini_erp_code.customer import Customer
from mini_erp_code.item import Item
from mini_erp_code.sales_order import SalesOrder
from mini_erp_code.system_user import SystemUser

class TestdbManager(unittest.TestCase):

    def setUp(self):
        self.customer_db = "mini_erp_code/database/customers.csv"
        self.user_db = "mini_erp_code/database/users.csv"
        self.item_db = "mini_erp_code/database/items.csv"
        self.sales_order_db = "mini_erp_code/database/sales_orders.csv"
        self.test_customers = [Customer('00001','Ville','Espoo','Tie 1','313','mail@email.com'), Customer('00002','Verneri','Vihti','Vihdintie 5','3456','nomail@email.com')]
        self.test_users = [SystemUser('00001','HeppuKoira','HeppuPeppu','0'), SystemUser('00002','NelliKoira','NelliPeppu','0')]
        self.test_new_customer = Customer("00003", "Vihtori", "Nokia", "Nokiantie 3 Nokia", "100", "vihtori.mail@nokia.fi")


    #Test loading customers with pseudo random selection of attributes(+ test that they are objects!)
    def test_load_customers(self):
        db_manger = DatabaseManager()
        customers = db_manger.load_customers()

        self.assertIsInstance(customers[0], Customer, 'Error loading customer objects!')
        self.assertIsInstance(customers[1], Customer, 'Error loading customer objects!')
        self.assertEqual(len(customers), 2, 'Error loading customer objects!')

        self.assertEqual(customers[0].customer_id, self.test_customers[0].customer_id, 'Error loading customer objects!')
        self.assertEqual(customers[0].name, self.test_customers[0].name, 'Error loading customer objects!')
        self.assertEqual(customers[0].city, self.test_customers[0].city, 'Error loading customer objects!')

        self.assertEqual(customers[1].customer_id, self.test_customers[1].customer_id, 'Error loading customer objects!')
        self.assertEqual(customers[1].name, self.test_customers[1].name, 'Error loading customer objects!')
        self.assertEqual(customers[1].city, self.test_customers[1].city, 'Error loading customer objects!')


    def test_load_users(self):
        db_manger = DatabaseManager()
        users = db_manger.load_users()
        self.assertIsInstance(users[0], SystemUser, 'Error loading user objects!')
        self.assertIsInstance(users[1], SystemUser, 'Error loading user objects!')
        self.assertEqual(len(users), 2, 'Error loading user objects!')

        self.assertEqual(users[0].user_id, self.test_users[0].user_id, 'Error loading user objects!')
        self.assertEqual(users[1].password, self.test_users[1].password, 'Error loading user objects!')
        self.assertEqual(users[0].access_level, self.test_users[0].access_level, "Error loading user object's access level! !")


    def test_load_items(self):
        db_manger = DatabaseManager()
        items = db_manger.load_items()
        self.assertIsInstance(items[0], Item, 'Error loading item objects!')

        self.assertIsInstance(items[1], Item, 'Error loading item objects!')
        self.assertEqual(len(items), 2, 'Error loading item objects!')


    def test_load_sales_orders(self):
        db_manger = DatabaseManager()
        sales_orders = db_manger.load_sales_orders()
        self.assertIsInstance(sales_orders[0], SalesOrder, 'Error loading sales_order objects!')

        self.assertEqual(len(sales_orders), 1, 'Error loading sales_order objects!')

############################################
    #Tesiting saving new info
    """To pass, the customers.csv needs to have only the first two customers set up.
     Seems to work well otherwise."""
    def test_save_new_customer(self):
        db_manger = DatabaseManager()
        db_manger.save_new_customer(self.test_new_customer.get_info())

        customers = db_manger.load_customers()
        self.assertEqual(customers[2].customer_id, self.test_new_customer.customer_id, 'Error loading customer objects!')

if __name__ == '__main__':
    unittest.main()