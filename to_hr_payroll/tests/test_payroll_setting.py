from odoo.tests import tagged
from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollSetting(TestPayrollCommon):

    def test_01_new_company(self):
        """
        Case 3: Kiểm tra dữ liệu sau khi tạo cty mới
            Input: Tạo công ty mới
            Ouput: Tạo mới các dữ liệu cho công ty này:
                - Đăng ký đóng góp
                - Kiểu đăng ký đóng góp từ lương
                - Mẫu chế độ đãi ngộ hợp đồng
                - Nhóm quy tắc lương
                - Cấu trúc lương cơ bản, cấu trúc lương cho từng chức vụ
                - Quy tắc lương cho cấu trúc lương cơ bản
                - Tạo ra mã trình tự 'salary.slip'
        """
        company = self.env['res.company'].create({
            'name': 'Test company 2'
            })

        # Check _generate_payrol_contribution_types
        contrib_type_data = company._prepare_payrol_contribution_types_data()
        contrib_types = self.env['hr.payroll.contribution.type'].search([('company_id', '=', company.id)])
        self.assertEqual(len(contrib_types), len(contrib_type_data), 'Test _generate_payrol_contribution_types not ok')
        msg = 'Test _generate_payrol_contribution_types not ok'
        for data in contrib_type_data:
            register = contrib_types.filtered(lambda r: r.name == data['name'])
            self.assertTrue(register, msg)
            self.assertEqual(register.code, data['code'], msg)

        # Check _generate_contribution_register
        contrib_register_data = company._prepare_contribution_register_data()
        contrib_registers = self.env['hr.contribution.register'].search([('company_id', '=', company.id)])
        self.assertEqual(len(contrib_registers), len(contrib_register_data), 'Test _generate_contribution_register not ok')
        msg = 'Test _generate_contribution_register not ok'
        for data in contrib_register_data:
            register = contrib_registers.filtered(lambda r: r.name == data['name'])
            self.assertTrue(register, msg)

        # check _generate_hr_advantage_templates
        advantage_template_data = company._prepare_hr_advantage_templates()
        advantage_templates = self.env['hr.advantage.template'].search([('company_id', '=', company.id)])
        self.assertEqual(len(advantage_template_data), len(advantage_templates), 'Test _generate_hr_advantage_templates not ok')
        msg = 'Test _generate_hr_advantage_templates not ok'
        for data in advantage_template_data:
            template = advantage_templates.filtered(lambda r: r.name == data['name'])
            self.assertTrue(template, msg)
            self.assertEqual(template.code, data['code'], msg)
            # ...

        # Check _generate_salary_rule_categories
        rule_categories_data = company._prepare_salary_rule_categories_data()
        rule_categories = self.env['hr.salary.rule.category'].search([('company_id', '=', company.id)])
        msg = 'Test _generate_salary_rule_categories not ok'
        children_code = ['ALW', 'DED_BEFORE_TAX', 'DED_AFTER_TAX', 'COMP', 'ALWNOTAX']
        for data in rule_categories_data:
            category = rule_categories.filtered(lambda r: r.code == data['code'])
            self.assertTrue(category, msg)
            if category.code in children_code:
                for line in data['children_ids']:
                    category = rule_categories.filtered(lambda r: r.code == line[2]['code'])
                    self.assertEqual(category.name, line[2]['name'], msg)
            else:
                self.assertEqual(category.name, data['name'], msg)

        # check base salary structures
        structures = self.env['hr.payroll.structure'].search([('company_id', '=', company.id)])
        base_structure = structures.filtered(lambda r: r.code == 'BASE')
        self.assertTrue(base_structure, 'Test salary structures for new company not ok')

        # check salary structures for jobs
        jobs = company._get_job_positions()
        job_structures = structures.filtered(lambda r: r.parent_id == base_structure)
        self.assertEqual(len(jobs), len(job_structures), 'Test salary structures for new company not ok')

        # check salary rules for base salary structures
        rule_data = company._parepare_salary_rules_vals_list(base_structure)
        rules = self.env['hr.salary.rule'].search([('company_id', '=', company.id)])
        self.assertEqual(len(rule_data), len(rules), 'Test salary rules for new company not ok')
        self.assertEqual(rules.struct_id, base_structure, 'Test salary rules for new company not ok')

        # check sequence
        sequence = self.env['ir.sequence'].search([('company_id', '=', company.id),
                                                   ('code', '=', 'salary.slip')])
        self.assertTrue(sequence, 'Test create sequence for new company not ok')

    def test_02_generate_payroll_rules(self):
        """
        Case 1: Test hành động "Generate Payroll Rules"
            Input: Truy cập vào Payroll Setting, nhấn nút "Generate Payroll Rules"
            Output:
                Tạo các đăng ký đóng góp nếu chưa có
                Tạo các kiểu đăng ký đóng góp từ lương nếu chưa có
                Tạo mẫu chế độ đãi ngộ hợp đồng nếu chưa có
                Tạo các nhóm quy tắc lương nếu chưa có
                Tạo cấu trúc lương, quy tắc lương cơ bản nếu chưa có
                Tạo cấu trúc lương cho từng chức vụ nếu chức vụ chưa có cấu lương
                    Cập nhật cấu trúc lương vào hợp đồng, nếu hợp đồng có gán đến chức vụ nếu có
        """
        # Prepare data
        company = self.env.company
        self.contract_open_emp_A.write({'job_id': self.job_product_dev.id})

        self.env['hr.advantage.template'].create({
            'name': 'New 1',
            'code': 'NEW1',
            'lower_bound': 0,
            'upper_bound': 100,
            'amount': 50
            })

        # Test
        company._generate_payroll_rules()

        # Check _generate_payrol_contribution_types
        contrib_type_data = company._prepare_payrol_contribution_types_data()
        contrib_types = self.env['hr.payroll.contribution.type'].search([('company_id', '=', company.id)])
        msg = 'Test _generate_payrol_contribution_types not ok'
        for data in contrib_type_data:
            register = contrib_types.filtered(lambda r: r.name == data['name'])
            self.assertTrue(register, msg)
            self.assertEqual(register.code, data['code'], msg)

        # Check _generate_contribution_register
        contrib_register_data = company._prepare_contribution_register_data()
        contrib_registers = self.env['hr.contribution.register'].search([('company_id', '=', company.id)])
        msg = 'Test _generate_contribution_register not ok'
        for data in contrib_register_data:
            register = contrib_registers.filtered(lambda r: r.name == data['name'])
            self.assertTrue(register, msg)

        # check _generate_hr_advantage_templates
        advantage_template_data = company._prepare_hr_advantage_templates()
        advantage_templates = self.env['hr.advantage.template'].search([('company_id', '=', company.id)])
        msg = 'Test _generate_hr_advantage_templates not ok'
        for data in advantage_template_data:
            template = advantage_templates.filtered(lambda r: r.name == data['name'])
            self.assertTrue(template, msg)
            self.assertEqual(template.code, data['code'], msg)
            # ...

        # Check _generate_salary_rule_categories
        rule_categories_data = company._prepare_salary_rule_categories_data()
        rule_categories = self.env['hr.salary.rule.category'].search([('company_id', '=', company.id)])
        msg = 'Test _generate_salary_rule_categories not ok'
        children_code = ['ALW', 'DED_BEFORE_TAX', 'DED_AFTER_TAX', 'COMP', 'ALWNOTAX']
        for data in rule_categories_data:
            category = rule_categories.filtered(lambda r: r.code == data['code'])
            self.assertTrue(category, msg)
            if category.code in children_code:
                for line in data['children_ids']:
                    category = rule_categories.filtered(lambda r: r.code == line[2]['code'])
                    self.assertEqual(category.name, line[2]['name'], msg)
            else:
                self.assertEqual(category.name, data['name'], msg)

        # check base salary structures
        structures = self.env['hr.payroll.structure'].search([('company_id', '=', company.id)])
        base_structure = structures.filtered(lambda r: r.code == 'BASE')
        self.assertTrue(base_structure, 'Test salary structures after generate payroll rules  not ok')

    def test_03_update_contracts_from_setting(self):
        """
        Case 2: Test hành động "Update Contracts"
            Input: Settings -> Payroll -> Mục "Automation" và bấm "Update Contracts"
            Output: Tất cả hợp đồng có trạng thái khác "đã hủy" sẽ được đánh dấu thay đổi trường "Tự động Tạo Phiếu lương" giống với Settings
        """
        company = self.env.company
        self.env['hr.contract'].search([('company_id', '=', self.env.company.id)]).write({
            'payslips_auto_generation': False
        })
        company.write({'payslips_auto_generation': True})
        company._sync_contract_payslips_auto_generation()

        self.assertTrue(self.contract_open_emp_A.payslips_auto_generation, 'Test method: _sync_contract_payslips_auto_generation not ok')
        self.assertTrue(self.contract_draft_emp_A.payslips_auto_generation, 'Test method: _sync_contract_payslips_auto_generation not ok')
        self.assertFalse(self.contract_cancel_emp_A.payslips_auto_generation, 'Test method: _sync_contract_payslips_auto_generation not ok')
        self.assertTrue(self.contract_close_emp_A.payslips_auto_generation, 'Test method: _sync_contract_payslips_auto_generation not ok')
