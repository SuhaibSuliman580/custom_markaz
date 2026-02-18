from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged, Form

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestHRContract(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestHRContract, cls).setUpClass()

        cls.struct_1 = cls.env['hr.payroll.structure'].create({
            'name': 'structure 2',
            'code': 'struct_2'
            })
        cls.struct_2 = cls.struct_1.copy()
        cls.struct_13th = cls.struct_1.copy()

        cls.struct_type_1 = cls.env['hr.payroll.structure.type'].create({
            'name': 'Structure Type 1',
            'property_regular_struct_id': cls.struct_1.id
        })
        cls.struct_type_2 = cls.env['hr.payroll.structure.type'].create({
            'name': 'Structure Type 2',
            'property_regular_struct_id': cls.struct_2.id,
            'property_thirteen_month_struct_id': cls.struct_13th.id
        })

        cls.contract_type_1 = cls.env['hr.contract.type'].create({
            'name': 'Contract type 1',
            'salary_computation_mode': 'day_basis',
            'personal_tax_policy': 'flat_rate'
        })

        cls.contract_type_2 = cls.env['hr.contract.type'].create({
            'name': 'Contract type 2',
            'salary_computation_mode': 'hour_basis',
            'personal_tax_policy': 'escalation'
        })

    def test_01_compute_wage(self):
        """
        Test: The wage salary is the same as the wage for the job Position when changing Job Position.
        """
        self.assertNotEqual(self.contract_draft_emp_A.wage, self.job_product_dev.wage)
        self.contract_draft_emp_A.job_id = self.job_product_dev
        self.assertEqual(self.contract_draft_emp_A.wage, self.job_product_dev.wage)

    def test_02_compute_contract_type_id(self):
        """
        Test: Tax, Tax Policy, Salary Computation Mode change when changing the contract type.
        compute: _compute_from_contract_type_id & _compute_tax_rule
        Input:
            1. changing `structure_type_id` field
            2. set structure_type_id = False
        Output:
            1. Tax Policy &Salary Computation Mode on the contract is the same as the selected contract type.
            2. No change
        """
        # 1.
        self.contract_draft_emp_A.contract_type_id = self.contract_type_1
        self.assertRecordValues(
            self.contract_draft_emp_A,
            [{
                'salary_computation_mode': self.contract_type_1.salary_computation_mode,
                'personal_tax_policy': self.contract_type_1.personal_tax_policy,
                'personal_tax_rule_id': self.contract_type_1.personal_tax_rule_id.id,
            }])

        self.contract_draft_emp_A.contract_type_id = self.contract_type_2
        self.assertRecordValues(
            self.contract_draft_emp_A,
            [{
                'salary_computation_mode': self.contract_type_2.salary_computation_mode,
                'personal_tax_policy': self.contract_type_2.personal_tax_policy,
                'personal_tax_rule_id': self.contract_type_2.personal_tax_rule_id.id,
            }])

        # 2.
        self.contract_draft_emp_A.contract_type_id = False
        self.assertRecordValues(
            self.contract_draft_emp_A,
            [{
                'salary_computation_mode': self.contract_type_2.salary_computation_mode,
                'personal_tax_policy': self.contract_type_2.personal_tax_policy,
                'personal_tax_rule_id': self.contract_type_2.personal_tax_rule_id.id,
            }])

    def test_03_compute_structure(self):
        """
        Test: The salary structure changes when changing the salary structure type.
        Input:
            - changing `structure_type_id` field.
        Output:
            - The salary structure on the contract is the same as
                the salary structure on the selected salary structure type.
        """
        self.contract_draft_emp_A.structure_type_id = self.struct_type_1
        self.assertRecordValues(
            self.contract_draft_emp_A,
            [{
                'struct_id': self.struct_1.id,
                'thirteen_month_struct_id': False,
            }])

        self.contract_draft_emp_A.structure_type_id = self.struct_type_2
        self.assertRecordValues(
            self.contract_draft_emp_A,
            [{
                'struct_id': self.struct_2.id,
                'thirteen_month_struct_id': self.struct_13th.id,
            }])

    def test_04_compute_gross_sal(self):
        """
        Test: The "Total Salary" calculation is based on the "Basic Wage" and "Monthly Advantages."
        Input:
            Case 1:
                - Basic Wage = 5000
                - Monthly Advantages: line 1: 100, line 2: 200
            Case 2:
                - Basic Wage = 6000
                - Monthly Advantages: line 1: 100, line 2: 200
            Case 3:
                - Basic Wage = 6000
                - Monthly Advantages: line 1: 300, line 2: 200
            Case 4:
                - Basic Wage = 6000
                - Monthly Advantages: line 1: 300, line 2: 100
        Output: Total Salary = Basic Wage + amount total of "Monthly Advantages"
            case 1: Total Salary = 5300$
            case 2: Total Salary = 6300$
            case 3 Total Salary = 6500$
            case 4: Total Salary = 6400$
        """
        advantages = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id)])
        with Form(self.contract_draft_emp_A) as f:
            f.wage = 5000
            self.assertEqual(5000, f.gross_salary, 'Test compute _compute_gross_sal not ok')
            with f.advantage_ids.new() as line:
                line.template_id = advantages[0]
                line.amount = 100
            with f.advantage_ids.new() as line:
                line.template_id = advantages[1]
                line.amount = 200
            # 5000 + 100 +200
            self.assertEqual(5300, f.gross_salary, 'Test compute _compute_gross_sal not ok')

            # 6000 + 100 +200
            f.wage = 6000
            self.assertEqual(6300, f.gross_salary, 'Test compute _compute_gross_sal not ok')

            # 6000 +300 +200
            with f.advantage_ids.edit(0) as line:
                line.amount = 300
            self.assertEqual(6500, f.gross_salary, 'Test compute _compute_gross_sal not ok')

            # 6000 + 300 + 100
            with f.advantage_ids.edit(1) as line:
                line.amount = 100
            self.assertEqual(6400, f.gross_salary, 'Test compute _compute_gross_sal not ok')

    def test_05_compute_payslips_auto_generation(self):
        """
        Test:The Payslips Auto-Generation field is set by default according to the company settings and can be changed.
            compute: _compute_payslips_auto_generation
        """
        f = Form(self.env['hr.contract'])
        self.assertFalse(f.payslips_auto_generation, 'Test default field: payslips_auto_generation not ok')

        self.env.company.write({'payslips_auto_generation': True})
        f = Form(self.env['hr.contract'])
        self.assertTrue(f.payslips_auto_generation, 'Test default field: payslips_auto_generation not ok')

    def test_06_compute_tax_rule_01(self):
        """
        Test: The "Tax Rule" field is calculated based on the country and Personal Tax Policy
        Input:
            1. All Tax Rules have fixed tax policies
            2. All Tax Rules are different from the company's country
        Output:
            - The Tax Rule field is left blank
        """
        TaxRule = self.env['personal.tax.rule']
        tax_rules = TaxRule.search([])
        tax_rules.write({'personal_tax_policy': 'flat_rate'})

        # 1.
        f = Form(self.env['hr.contract'], view="hr_contract.hr_contract_view_form")
        f.employee_id = self.product_emp_A
        f.personal_tax_policy = 'escalation'
        self.assertFalse(f.personal_tax_rule_id, 'Test compute _compute_tax_rule not ok')

        # 2.
        tax_rules.write({
            'country_id': self.env.ref('base.dz').id
        })
        TaxRule = self.env['personal.tax.rule']
        f = Form(self.env['hr.contract'], view="hr_contract.hr_contract_view_form")
        f.employee_id = self.product_emp_A
        f.personal_tax_policy = 'escalation'
        self.assertFalse(f.personal_tax_rule_id, 'Test compute _compute_gross_sal not ok')
        f.personal_tax_policy = 'flat_rate'
        self.assertFalse(f.personal_tax_rule_id, 'Test compute _compute_gross_sal not ok')

    def test_06_compute_tax_rule_02(self):
        """
        Test: The "Tax Rule" field is calculated based on the country and Personal Tax Policy
        Input:
            - There can be one or multiple tax rules
        Output:
            - default to the first tax rule in priority order.
        """
        TaxRule = self.env['personal.tax.rule']
        TaxRule.create({'country_id': self.product_emp_A.country_id.id, 'sequence': 3})
        tax2 = TaxRule.create({'country_id': self.product_emp_A.country_id.id, 'sequence': -999})
        TaxRule.search([]).write({'personal_tax_policy': 'flat_rate'})

        f = Form(self.env['hr.contract'], view="hr_contract.hr_contract_view_form")
        f.employee_id = self.product_emp_A
        f.personal_tax_policy = 'flat_rate'
        self.assertEqual(f.personal_tax_rule_id, tax2, 'Test compute _compute_tax_rule not ok')

    def test_07_generate_payroll_contribution_registers_01(self):
        """
        Case 1: Test hành động "Generate Payroll Contribution Registers" trong tab "Contribution Registers"
            TH1: Hợp đồng không có "Payroll Contribution Types"
                => không tạo đăng ký đóng góp từ lương
        """
        contract = self.contract_open_emp_A
        contract.generate_payroll_contribution_registers()
        self.assertFalse(contract.payroll_contribution_register_ids, 'Test method: generate_payroll_contribution_registers not ok')

    def test_07_generate_payroll_contribution_registers_02(self):
        """
        Case 1: Test hành động "Generate Payroll Contribution Registers" trong tab "Contribution Registers"
            TH2. Hợp đồng có kiểu đóng góp, nhưng chưa có đăng ký đóng góp liên quan đến kiểu đóng góp đã chọn
                => Tạo ra các đăng ký đóng góp liên quan đến kiểu đóng góp ở trạng thái dự thảo
        """
        contract = self.contract_open_emp_A
        contribution_types = self.env['hr.payroll.contribution.type'].search([('company_id', '=', self.env.company.id)])
        contract.write({'payroll_contribution_type_ids': [(6, 0, contribution_types.ids)]})

        contract.generate_payroll_contribution_registers()

        self.assertEqual(
            contract.payroll_contribution_type_ids,
            contract.payroll_contribution_register_ids.type_id,
            'Test method: generate_payroll_contribution_registers not ok')

        state = set(contract.payroll_contribution_register_ids.mapped('state'))
        self.assertEqual({'draft'}, state, 'Test method: generate_payroll_contribution_registers not ok')

    def test_07_generate_payroll_contribution_registers_03(self):
        """
        Case 1: Test hành động "Generate Payroll Contribution Registers" trong tab "Contribution Registers"
            TH3: Hợp đồng có kiểu đóng góp, đã có đắng ký đóng góp liên quan đến kiểu đóng góp
            Output:
                những đăng ký đóng góp cũ liên quan đến kiểu đóng góp giữ nguyên,
                những kiểu đăng ký đóng góp chưa có đăng ký đóng góp sẽ tạo mới
        """
        contract = self.contract_open_emp_A
        contribution_types = self.env['hr.payroll.contribution.type'].search([('company_id', '=', self.env.company.id)])
        contract.write({'payroll_contribution_type_ids': [(6, 0, contribution_types[1].ids)]})

        contract.generate_payroll_contribution_registers()
        contract.payroll_contribution_register_ids.action_confirm()

        # old data
        old_register_ids = contract.payroll_contribution_register_ids
        old_record_state = set(old_register_ids.mapped('state'))

        contract.write({'payroll_contribution_type_ids': [(6, 0, contribution_types.ids)]})
        contract.generate_payroll_contribution_registers()

        # new data
        new_register_ids = contract.payroll_contribution_register_ids
        new_record_state = set((new_register_ids - old_register_ids).mapped('state'))

        self.assertEqual(
            contract.payroll_contribution_type_ids,
            contract.payroll_contribution_register_ids.type_id,
            'Test method: generate_payroll_contribution_registers not ok')

        self.assertEqual({'draft'}, new_record_state, 'Test method: generate_payroll_contribution_registers not ok')
        self.assertEqual({'confirmed'}, old_record_state, 'Test method: generate_payroll_contribution_registers not ok')

    def test_08_compute_payslips_count(self):
        """
        Case 6: Test tính toán Số lượng phiếu lương trên hợp đồng
        """
        self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-07-01'),
            fields.Date.to_date('2021-07-30'))
        self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-06-01'),
            fields.Date.to_date('2021-06-30'))
        self.contract_open_emp_A.flush_recordset()
        self.assertEqual(2, self.contract_open_emp_A.payslips_count, 'Test payslip count not ok')

    def test_09_unlink_except_contract_with_payslip_01(self):
        """
        Case 2: Test Xóa Hợp đồng
            TH1: Hợp đồng không liên quan đến phiếu lương nào
                Ouput: Xóa hợp đồng thành công
        """
        self.assertTrue(self.contract_cancel_emp_A.unlink)

    def test_09_unlink_except_contract_with_payslip_02(self):
        """
        Case 2: Test Xóa Hợp đồng
            TH2: Hợp đồng có liên quan đến phiếu lương
                Ouput: Xóa hợp đồng không thành công
        """
        payslip1 = self.create_payslip(self.product_emp_A.id,
                            fields.Date.to_date('2021-07-01'),
                            fields.Date.to_date('2021-07-30'))

        # use flush to update the relationship between payslip and contract
        payslip1.flush_recordset()
        self.contract_open_emp_A.write({'state': 'cancel'})
        with self.assertRaises(UserError):
            self.contract_open_emp_A.unlink()

    def test_10_compute_included_in_payroll_contribution_register(self):
        """
        Test: Trường `bao gồm trong đăng ký đóng góp từ lương`
        Input:
            Mẫu phụ cấp TRAVEL cho hợp đồng có đánh dấu là `bao gồm trong đăng ký đóng góp từ lương`
            Mẫu phụ cấp PHONE cho hợp đồng không đánh dấu là `bao gồm trong đăng ký đóng góp từ lương`
            Mẫu phụ cấp MEAL cho hợp đồng không đánh dấu là `bao gồm trong đăng ký đóng góp từ lương`
            Trên hợp đồng, chọn mẫu đãi ngộ có mẫu phụ cấp: TRAVEL, PHONE, MEAL
            * với đãi ngộ MEAL, đánh dấu `bao gồm trong đăng ký đóng góp từ lương` trên hợp đồng

        Output:
            Dòng đãi ngộ của hợp đồng (TRAVEL), Trường `bao gồm trong đăng ký đóng góp từ lương` là True
            Dòng đãi ngộ của hợp đồng (PHONE), Trường `bao gồm trong đăng ký đóng góp từ lương` là False
            Dòng đãi ngộ của hợp đồng (MEAL), Trường `bao gồm trong đăng ký đóng góp từ lương` là True
            Mẫu phụ cấp (MEAL), Trường `bao gồm trong đăng ký đóng góp từ lương` là False
        """
        AdvantageTemplate = self.env['hr.advantage.template']
        advantage_travel = AdvantageTemplate.search([('company_id', '=', self.env.company.id), ('code', '=', 'TRAVEL')])
        advantage_travel.included_in_payroll_contribution_register = True
        advantage_phone = AdvantageTemplate.search([('company_id', '=', self.env.company.id), ('code', '=', 'PHONE')])
        advantage_meal = AdvantageTemplate.search([('company_id', '=', self.env.company.id), ('code', '=', 'MEAL')])
        self.contract_open_emp_A.write({
            'advantage_ids': [
                                (0, 0, {'template_id': advantage_travel.id, 'amount': 500}),
                                (0, 0, {'template_id': advantage_phone.id, 'amount': 500}),
                                (0, 0, {'template_id': advantage_meal.id, 'amount': 500, 'included_in_payroll_contribution_register': True}),
                            ],
        })

        self.assertRecordValues(
            self.contract_open_emp_A.advantage_ids,
            [{
                'included_in_payroll_contribution_register': True,
            },
            {
                'included_in_payroll_contribution_register': False,
            },
            {
                'included_in_payroll_contribution_register': True,
            }])
        self.assertFalse(advantage_meal.included_in_payroll_contribution_register)

    def test_11_compute_amount_of_contribution_register_01(self):
        """
        Test: Cơ sở tính toán của đăng ký đóng góp lương phụ thuộc vào trường đánh dấu "bao gồm trong đăng ký đóng góp từ lương"
        Input:
            Hợp đồng lương 10000, chưa có kiểu và đăng ký đóng góp từ lương
            Phụ cấp TRAVEL cho hợp đồng là 500, không đánh dấu là bao gồm trong đăng ký đóng góp từ lương
            Chọn kiểu đăng ký đóng góp từ lương
            Nhấn chọn tạo đăng ký đóng góp từ lương
        Output:
            => Tạo ra các dòng đăng ký đóng góp từ lương với cơ sở tính toán là 10000
        """
        contract = self.contract_open_emp_A
        advantage = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id), ('code', '=', 'TRAVEL')])
        contribution_types = self.env['hr.payroll.contribution.type'].search([('company_id', '=', self.env.company.id)], limit=4)
        contract.write({
            'wage': 10000,
            'advantage_ids': [(0, 0, {'template_id': advantage.id, 'amount': 500, 'included_in_payroll_contribution_register': False})],
            'payroll_contribution_type_ids': [(6, 0, contribution_types.ids)]
        })
        contract.generate_payroll_contribution_registers()
        self.assertRecordValues(
            contract.payroll_contribution_register_ids,
            [{
                'contribution_base': 10000,
            },
            {
                'contribution_base': 10000,
            },
            {
                'contribution_base': 10000,
            },
            {
                'contribution_base': 10000,
            }])

    def test_11_compute_amount_of_contribution_register_02(self):
        """
        Test: Cơ sở tính toán của đăng ký đóng góp lương phụ thuộc vào trường đánh dấu "bao gồm trong đăng ký đóng góp từ lương"
        Input:
            Hợp đồng lương 10000, chưa có kiểu và đăng ký đóng góp từ lương
            Phụ cấp TRAVEL cho hợp đồng là 500, có đánh dấu là bao gồm trong đăng ký đóng góp từ lương
            Chọn kiểu đăng ký đóng góp từ lương
            Nhấn chọn tạo đăng ký đóng góp từ lương
        Output:
            => Tạo ra các dòng đăng ký đóng góp từ lương với cơ sở tính toán là 10500
        """
        contract = self.contract_open_emp_A
        advantage = self.env['hr.advantage.template'].search([('company_id', '=', self.env.company.id), ('code', '=', 'TRAVEL')])
        contribution_types = self.env['hr.payroll.contribution.type'].search([('company_id', '=', self.env.company.id)], limit=4)
        contract.write({
            'wage': 10000,
            'advantage_ids': [(0, 0, {'template_id': advantage.id, 'amount': 500, 'included_in_payroll_contribution_register': True})],
            'payroll_contribution_type_ids': [(6, 0, contribution_types.ids)]
        })
        contract.generate_payroll_contribution_registers()
        self.assertRecordValues(
            contract.payroll_contribution_register_ids,
            [{
                'contribution_base': 10500,
            },
            {
                'contribution_base': 10500,
            },
            {
                'contribution_base': 10500,
            },
            {
                'contribution_base': 10500,
            }])
