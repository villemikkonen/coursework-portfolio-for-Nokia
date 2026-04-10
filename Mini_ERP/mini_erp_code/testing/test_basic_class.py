import unittest

from mini_erp_code.customer import  Customer
from mini_erp_code.system_user import SystemUser
from mini_erp_code.item import Item

class TestBasicClasses(unittest.TestCase):


    def test_customer(self):
        a = Customer('00001', 'Ville', 'Espoo', 'tie 1', '313', 'mail@email.com')

        self.assertEqual(a.get_info(), ['Ville', 'Espoo', 'tie 1', '313', 'mail@email.com'], 'Customer information is wrong')

    def test_change_customer_info(self):
        a = Customer('00001', 'Ville', 'Espoo', 'tie 1', '313', 'mail@email.com')
        a.name = 'Heppu'
        a.city = 'Helsinki'
        a.address = 'tietotie 3000'
        a.phone = '0101'
        a.email = ''

        self.assertEqual(a.get_info(),['Heppu', 'Helsinki', 'tietotie 3000', '0101', '' ],
                         'Customer info change not working correctly' )



    def test_system_user(self):
        user_a = SystemUser('00001', 'Valtteri', 'A-mies')

        self.assertEqual(user_a.name, 'Valtteri', 'System user info wrong' )
        self.assertEqual(user_a.user_id, '00001', 'System user info wrong' )
        self.assertEqual(user_a.access_level, 0, 'System user info wrong' )

    def test_set_access_level(self):
        user_a = SystemUser('00001', 'Valtteri', 'A-mies')
        user_a.set_access_level(3)
        self.assertEqual(user_a.access_level, 3, 'Access level setting error' )

        user_a.set_access_level(2)
        self.assertEqual(user_a.access_level, 2, 'Access level setting error' )


    def test_item(self):
        first_item = Item('00001', 'bar', '100', 10)

        self.assertEqual(first_item.item_id, '00001', 'Item info wrong' )
        self.assertEqual(first_item.name, 'bar', 'Item info wrong' )
        self.assertEqual(first_item.quantity, 10, 'Item info wrong' )


    def test_stock_controls(self):
        item_i = Item('00001', 'bar', '100', 10)

        item_i.add_stock(10)
        item_i.add_stock(20)

        item_i.remove_stock(50)

        self.assertEqual(item_i.quantity, (10+10+20-50), 'Stock level control error')







if __name__ == '__main__':
    unittest.main()