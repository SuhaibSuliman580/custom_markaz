from odoo.tests.common import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestDataAfterInstall(TransactionCase):

    def test_01_check_data_after_install(self):
        """
        Case 1: Kiểm tra nhóm quy tắc lương "HR Meal Order Deduction"
        - Input: Truy cập nhóm quy tắc lương
        - Output: Nhóm quy tắc lương "HR Meal Order Deduction" được tạo ra mã là MODED
        """
        salary_rule_category = self.env['hr.salary.rule.category'].search([('code', '=', 'MODED')], limit=1)
        self.assertTrue(salary_rule_category)

    def test_02_check_data_after_install(self):
        """
        Case 2: Kiểm tra quy tắc lương "HR Meal Order Deduction Amount"
        - Input: Truy cập quy tắc lương
        - Output: Quy tắc lương "HR Meal Order Deduction Amount" được tạo ra mã là MODED
        """
        salary_rule = self.env['hr.salary.rule'].search([('code', '=', 'MODED')], limit=1)
        self.assertTrue(salary_rule)

    def test_03_check_data_after_install(self):
        """
        Case 3: Kiểm tra nhóm ghi nhận đóng góp "HR Meal Order Deduction"
        - Input: Truy cập nhóm ghi nhận đóng góp
        - Output: Nhóm ghi nhận đóng góp "HR Meal Order Deduction" được tạo ra
        """
        contribution_category = self.env.ref('to_hr_payroll_meal.hr_contribution_category_deduction')
        self.assertTrue(contribution_category)

    def test_04_check_data_after_install(self):
        """
        Case 4: Kiểm tra ghi nhận đóng góp "HR Meal Order Deduction"
        - Input: Truy cập ghi nhận đóng góp
        - Output: Ghi nhận đóng góp "HR Meal Order Deduction" được tạo ra
        """
        contribution_category = self.env.ref('to_hr_payroll_meal.hr_contribution_category_deduction')
        contribution = self.env['hr.contribution.register'].search([('category_id', '=', contribution_category.id)], limit=1)
        self.assertTrue(contribution)
