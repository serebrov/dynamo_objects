import unittest
from dynamo_objects import database
from .base import BaseDynamoTest
from .schema import CustomerTable, Customer


class UpdateCountersTest(BaseDynamoTest):

    def setUp(self):
        super(UpdateCountersTest, self).setUp()
        self.table = CustomerTable()
        self.customer = Customer(customer_id='CUSTOMER1')
        self.customer.thanks_count = 0
        self.table.save(self.customer)

    def test_raw(self):
        self.db.get_connection().update_item(
            self.db.get_table_name('customer'),
            {'customer_id': 'CUSTOMER1'},
            update_expression='SET #count = #count + :inc ',
            expression_attribute_names={'#count': 'thanks_count'},
            expression_attribute_values={':inc': {'N': 1}},
            return_values="UPDATED_NEW")
        customer = self.table.get('CUSTOMER1')
        self.assertEquals(1, customer.thanks_count)

    def test_counter(self):
        self.table.update_counter('CUSTOMER1', thanks_count=1)
        customer = self.table.get('CUSTOMER1')
        self.assertEquals(1, customer.thanks_count)

    def test_counter_by_ten(self):
        self.table.update_counter('CUSTOMER1', thanks_count=5)
        customer = self.table.get('CUSTOMER1')
        self.assertEquals(5, customer.thanks_count)
        self.table.update_counter('CUSTOMER1', thanks_count=5)
        customer = self.table.get('CUSTOMER1')
        self.assertEquals(10, customer.thanks_count)

    def test_counter_dec(self):
        self.table.update_counter('CUSTOMER1', thanks_count=5)
        self.table.update_counter('CUSTOMER1', thanks_count=-1)
        customer = self.table.get('CUSTOMER1')
        self.assertEquals(4, customer.thanks_count)


if __name__ == "__main__":
    unittest.main()
