from odoo.tests.common import tagged, Form

from .common import Common


@tagged('-at_install', 'post_install')
class TestContract(Common):

    def test_01_check_contract(self):
        """
        Case 1: Kiểm tra thay đổi tiền cho mỗi bữa ăn trên hợp đồng khi chưa đặt giá mặc định trên công ty
        - Input: Thực hiện tạo hợp đồng
        - Output: Trường tiền cho mỗi bữa ăn trên hợp đồng bằng 0.0
        """
        contract_form = Form(self.env['hr.contract'])
        self.assertEqual(contract_form.pay_per_meal, 0.0)

    def test_02_check_contract(self):
        """
        Case 2: Kiểm tra thay đổi tiền cho mỗi bữa ăn trên hợp đồng khi đã đặt giá mặc định trên công ty
        - Input: Thực hiện tạo hợp đồng
        - Output: Trường tiền cho mỗi bữa ăn trên hợp đồng bằng giá mặc định đã đặt
        """
        self.env.company.write({'meal_emp_price': 100})
        contract_form = Form(self.env['hr.contract'])
        self.assertEqual(contract_form.pay_per_meal, 100)
