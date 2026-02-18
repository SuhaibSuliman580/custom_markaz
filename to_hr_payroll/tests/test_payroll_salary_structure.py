from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollSalaryStructure(TestPayrollCommon):

    def test_01_salary_structure_recursion(self):
        """
        Test đệ quy cấu trúc lương
        """
        Structure = self.env['hr.payroll.structure']
        structure_1 = Structure.create({'name': 'Test 1', 'code': 'TEST1'})
        structure_2 = Structure.create({'name': 'Test 1', 'code': 'TEST1',
                                        'parent_id': structure_1.id})
        structure_3 = Structure.create({'name': 'Test 1', 'code': 'TEST1',
                                        'parent_id': structure_2.id})

        with self.assertRaises(ValidationError):
            structure_1.write({'parent_id': structure_2.id})
        with self.assertRaises(ValidationError):
            structure_1.write({'parent_id': structure_3.id})
        with self.assertRaises(ValidationError):
            structure_2.write({'parent_id': structure_3.id})

    def test_02_salary_structure_duplicate(self):
        """
        Test nhân bản cấu trúc lương
        => Trường Tên/Tham chiếu của bản sao là Tên/Tham chiếu của bản gốc + "(Sao chép)"
        """
        # Case 2: Test nhân bản
        structure_new = self.structure_base.copy()
        self.assertEqual(structure_new.name, self.structure_base.name + " (copy)", 'Test duplicate Salary Structure not ok')
        self.assertEqual(structure_new.code, self.structure_base.code + " (copy)", 'Test duplicate Salary Structure not ok')

    def test_03_salary_structure_archive(self):
        """
        Test Lưu trữ / Thôi lưu trữ
        => Cấu trúc lương và tất cả quy tắc lương liên quan sẽ ở tình trạng Lưu trữ/Thôi lưu trữ
        """
        rules = self.structure_base.rule_ids

        # archived
        self.structure_base.toggle_active()
        self.assertFalse(self.structure_base.active, 'Test Archive Salary Structure not ok')
        rules_active = set(rules.mapped('active'))
        self.assertEqual({False}, rules_active, 'Test Archive not ok')

        # Unarchive
        self.structure_base.toggle_active()
        self.assertTrue(self.structure_base.active, 'Test Archive  Salary Structure not ok')
        self.assertEqual(rules, self.structure_base.rule_ids, 'Test Archive Salary Structure not ok')

    def test_04_salary_structure_unlink(self):
        """
        Test Xóa cấu trúc lương dẫn đến xóa quy tắc lương liên quan đến nó
        Input:
            - Xóa cấu trúc lương
        Output:
            - Xóa cấu trúc lương và tất cả quy tắc lương liên quan đến cấu trúc lương này ,
            bao gồm cả các quy tắc lương đã lưu trữ
        """
        structure_base = self.structure_base.copy()
        rules = structure_base.rule_ids
        rules[1].toggle_active()

        rules_archived = self.env['hr.salary.rule'].with_context(active_test=False).search([
            ('company_id', '=', self.env.company.id),
            ('struct_id', '=', structure_base.id)
        ])

        structure_base.unlink()
        self.assertFalse(structure_base.exists(), 'Test Unlink Salary Structure not ok')
        self.assertFalse(rules_archived.exists(), 'Test Unlink Salary Structure not ok')

    def test_05_salary_structure_reset(self):
        """
        Test hành động "Reset Rules"
        Inout:
            Nhấn nút "Reset Rules"
        Output:
            Đặt lại toàn bộ các quy tắc lương trong cấu trúc này về giá trị mặc định như khi cài mới,
            tất cả các tùy chỉnh sẽ bị mất đi,
            áp dụng cho 1 số trường sau: Điều kiện dựa trên, điều kiện Python, Kiểu tổng, Mã Python, Xuất hiện trong phiếu lương
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
        structure_base.action_reset_rules()

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
