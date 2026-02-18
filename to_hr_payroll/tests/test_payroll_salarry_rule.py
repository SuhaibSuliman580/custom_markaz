from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError, UserError
from odoo.tools import mute_logger
from odoo.tests import tagged, Form

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollSalaryRule(TestPayrollCommon):

    def test_01_compute_paid_by_company(self):
        """
        Test _compute_paid_by_company: Trường "Paid by Company" thay đổi theo nhóm cha
        Input:
            - Tạo 1 nhóm quy tắc lương mới (A)
            1. Trường Cấp cha chọn 1 nhóm quy tắc lương (B) có đánh dấu thanh toán bởi công ty
            2. Trường Cấp cha chọn 1 nhóm quy tắc lương (C) không đánh dấu thanh toán bởi công ty
        Ouput:
            1. Nhóm quy tắc lương (A) có đánh dấu thanh toán bởi công ty
            2. Nhóm quy tắc lương (A) không đánh dấu thanh toán bởi công ty
        """
        Category = self.env['hr.salary.rule.category']
        rule_category_B = Category.create({
            'name': 'Category B',
            'code': 'CB',
            'paid_by_company': True
        })
        rule_category_C = Category.create({
            'name': 'Category C',
            'code': 'CC',
            'paid_by_company': False
        })

        f = Form(Category)
        f.name = 'Category A'
        f.code = 'CA'

        f.parent_id = rule_category_C
        self.assertFalse(f.paid_by_company)

        f.parent_id = rule_category_B
        self.assertTrue(f.paid_by_company)

        f.paid_by_company = False
        category = f.save()
        self.assertFalse(category.paid_by_company)

    def test_02_salary_rule_category_recusion(self):
        """
        Test _check_parent_id: Check đệ quy trường `parent_id`
        """
        Category = self.env['hr.salary.rule.category']
        # Case 1: Test đệ quy
        category1 = Category.create({'name': 'Test 1', 'code': 'TEST1'})
        category2 = Category.create({'name': 'Test 2', 'code': 'TEST2', 'parent_id': category1.id})
        category3 = Category.create({'name': 'Test 3', 'code': 'TEST3', 'parent_id': category2.id})
        with self.assertRaises(ValidationError):
            category1.write({'parent_id': category2.id})
        with self.assertRaises(ValidationError):
            category1.write({'parent_id': category3.id})
        with self.assertRaises(ValidationError):
            category2.write({'parent_id': category3.id})

    @mute_logger('odoo.sql_db')
    def test_03_code_unique_per_company_01(self):
        """
        Test: Test trường Mã  (Code) là duy nhất theo công ty
        Input:
            Tạo 1 nhóm quy tắc lương mới, trùng với mã của nhóm quy tắc trên hệ thống cùng công ty
        Output:
            Ngoại lệ
        """
        Category = self.env['hr.salary.rule.category']
        Category.create({'name': 'Test 1', 'code': 'TEST1'})
        with self.assertRaises(IntegrityError):
            Category.create({'name': 'Test 4', 'code': 'TEST1'})

    def test_03_code_unique_per_company_02(self):
        """
        Test: Test trường Mã  (Code) là duy nhất theo công ty
        Input:
            Tạo 1 nhóm quy tắc lương mới, trùng với mã của nhóm quy tắc trên hệ thống khác công ty
        Output:
            Thành công
        """
        Category = self.env['hr.salary.rule.category']
        Category.create({'name': 'Test 1', 'code': 'TEST1'})
        company2 = self.env['res.company'].create({'name': 'Company 2'})

        category = Category.create({'name': 'Test 3', 'code': 'TEST1', 'company_id': company2.id})
        self.assertTrue(category, 'Test rule category code not ok')

    def test_04_compute_salary_rules_count(self):
        """
        Test _compute_salary_rules_count: số lượng quy tắc lương của nhóm quy tắc lương
        """
        Category = self.env['hr.salary.rule.category']
        category1 = Category.create({'name': 'Test 1', 'code': 'TEST1'})
        category2 = Category.create({'name': 'Test 2', 'code': 'TEST2'})

        vals = [
            self.prepare_rule_data('Test Rule 1', 'R1', self.structure_base.id, category1.id),
            self.prepare_rule_data('Test Rule 2', 'R2', self.structure_base.id, category2.id),
            self.prepare_rule_data('Test Rule 3', 'R3', self.structure_base.id, category1.id),
            self.prepare_rule_data('Test Rule 4', 'R4', self.structure_base.id, category2.id),
            self.prepare_rule_data('Test Rule 5', 'R5', self.structure_base.id, category2.id),
        ]
        self.env['hr.salary.rule'].create(vals)
        self.assertEqual(2, category1.salary_rules_count, 'Test the number of salary rules of the category not ok')
        self.assertEqual(3, category2.salary_rules_count, 'Test the number of salary rules of the category not ok')

    def test_05_salary_rule_reset(self):
        """
        Test nút "Reset" quy tắc lương
        Input:
            Nhấn nút "Reset" trên quy tắc lương
        Output:
            - Đặt lại quy tắc lương này về giá trị mặc định như khi cài mới,
            tất cả các tùy chỉnh sẽ bị mất đi,
            - Áp dụng cho 1 số trường sau: Điều kiện dựa trên, điều kiện Python, Kiểu tổng, Mã Python, Xuất hiện trong phiếu lương
        """
        structure_base = self.structure_base
        rules = structure_base.rule_ids
        rule_data = self.env.company._parepare_salary_rules_vals_list(structure_base)
        rules.write({
            'condition_select': 'range',
            'condition_python': 'Test condition_python',
            'amount_select': 'code',
            'appears_on_payslip': False,
            'amount_python_compute': 'Test amount_python_compute',
        })
        rules.action_reset()

        # test
        for data in rule_data:
            rule = rules.filtered(lambda r: r.code == data['code'])
            if rule:
                vals = {}
                if data.get('condition_select', False):
                    vals['condition_select'] = data['condition_select']
                if data.get('condition_python', False):
                    vals['condition_python'] = data['condition_python']
                if data.get('amount_select', False):
                    vals['amount_select'] = data['amount_select']
                if data.get('appears_on_payslip', False):
                    vals['appears_on_payslip'] = data['appears_on_payslip']
                if data.get('amount_python_compute', False):
                    vals['amount_python_compute'] = data['amount_python_compute']
                if vals:
                    self.assertRecordValues(rule, [vals])

    def test_06_unlink_salary_rule_01(self):
        """
        Test: Xóa quy tắc lương không thành công do liên quan đến phiếu lương
        Input:
            Quy tắc lương có liên quan đến dòng phiếu lương
        Output:
            Thất bại, thông báo ngoại lệ
        """
        payslip1 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-07-01'),
            fields.Date.to_date('2021-07-30'))
        payslip1.compute_sheet()

        rule_ids = payslip1.line_ids.salary_rule_id
        self.assertRaises(UserError, rule_ids.unlink)

    def test_06_unlink_salary_rule_02(self):
        """
        Test: Xóa quy tắc lương thành công khi chưa liên kết đến phiếu lương
        Input:
            Quy tắc lương không liên quan đến bất kỳ dòng phiếu lương nào
        Output:
            Xóa thành công
        """
        rules = self.env['hr.salary.rule'].search([('payslip_line_ids', '=', False)])
        self.assertTrue(rules)  # ensure we have rules found
        self.assertTrue(rules.unlink(), 'Test unlink Salary Rule not ok')

    def test_07_create_salary_rule_with_contrib_register_01(self):
        """
        Test Tạo bản ghi với trường "Ghi nhận đóng góp"
        Input:
            Tạo quy tắc lương, chọn đăng ký đóng góp.
            Nhóm của Ghi nhận đóng góp không đánh dấu là "bắt buộc yêu cầu đối tác"
        Output: Tạo thành công
        """
        rule_category = self.env['hr.salary.rule.category'].search([('company_id', '=', self.env.company.id)], limit=1)
        contribution = self.env['hr.contribution.register'].search([('company_id', '=', self.env.company.id)], limit=1)
        contribution.category_id.write({'partner_required': False})

        rule = self.create_rule('Test Rule 1', 'T1', self.structure_base.id, rule_category.id, register_id=contribution.id)
        self.assertTrue(rule, 'Test create Rule with Contribution Register not ok')

    def test_07_create_salary_rule_with_contrib_register_02(self):
        """
        Test Tạo bản ghi với trường "Ghi nhận đóng góp"
        Input:
            Tạo quy tắc lương, chọn đăng ký đóng góp.
            Nhóm của Ghi nhận đóng góp đánh dấu là "bắt buộc yêu cầu đối tác", và có chọn đối tác
        Output: Tạo thành công
        """
        rule_category = self.env['hr.salary.rule.category'].search([('company_id', '=', self.env.company.id)], limit=1)
        contribution = self.env['hr.contribution.register'].search([('company_id', '=', self.env.company.id)], limit=1)
        contribution.category_id.write({'partner_required': True})
        partner = self.env['res.partner'].sudo().create({'name': 'Test Partner 1'})
        contribution.write({'partner_id': partner.id})

        rule = self.create_rule('Test Rule 1', 'T1', self.structure_base.id, rule_category.id, register_id=contribution.id)
        self.assertTrue(rule, 'Test create Rule with Contribution Register not ok')

    def test_07_create_salary_rule_with_contrib_register_03(self):
        """
        Test Tạo bản ghi với trường "Ghi nhận đóng góp"
        Input:
            Tạo quy tắc lương, chọn đăng ký đóng góp.
            Nhóm của Ghi nhận đóng góp đánh dấu là "bắt buộc yêu cầu đối tác", và có không chọn đối tác
        Output: Tạo không thành công
        """
        rule_category = self.env['hr.salary.rule.category'].search([('company_id', '=', self.env.company.id)], limit=1)
        contribution = self.env['hr.contribution.register'].search([('company_id', '=', self.env.company.id)], limit=1)
        contribution.category_id.write({'partner_required': True})

        with self.assertRaises(ValidationError):
            self.create_rule('Test Rule 1', 'T1', self.structure_base.id, rule_category.id, register_id=contribution.id)
