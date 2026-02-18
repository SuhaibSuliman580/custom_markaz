from odoo import fields
from odoo.exceptions import ValidationError

from .common import TestPayrollCommon, ADVANTAGE_CODE_LIST


class TestPayslipMultiContracts(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayslipMultiContracts, cls).setUpClass()

        cls.employee_B = cls.create_employee(
            'Employee B',
            job_id=cls.job_product_dev.id)

        # """
        # 2 Tax rules
        # """
        TaxRule = cls.env['personal.tax.rule']
        cls.tax_flat_rate = TaxRule.create({
            'country_id': cls.env.company.country_id.id,
            'personal_tax_policy': 'flat_rate',
            'personal_tax_flat_rate': 10.0,
            'apply_tax_base_deduction': False,
            })
        cls.tax_escalation = TaxRule.create({
            'country_id': cls.env.company.country_id.id,
            'personal_tax_policy': 'escalation',
            'apply_tax_base_deduction': True,
            'personal_tax_base_ded': 11000000,
            'dependent_tax_base_ded': 4400000,
            'progress_ids': [
                    (0, 0, {'base': 0, 'rate': 5.0}),
                    (0, 0, {'base': 5000000, 'rate': 10.0}),
                    (0, 0, {'base': 10000000, 'rate': 15.0}),
                    (0, 0, {'base': 18000000, 'rate': 20.0})
                ]
        })

        # """
        # 3 contracts in 2022
        # """
        cls.contract_B_trial = cls.create_contract(
            cls.employee_B.id,
            fields.Date.to_date('2022-01-01'),
            fields.Date.to_date('2022-02-28'),
            wage=10000000,
            state='close')
        cls.contract_B_trial.personal_tax_rule_id = cls.tax_flat_rate

        cls.contract_B_01 = cls.create_contract(
            cls.employee_B.id,
            fields.Date.to_date('2022-03-01'),
            fields.Date.to_date('2022-05-10'),
            wage=15000000,
            state='close')
        cls.contract_B_02 = cls.create_contract(
            cls.employee_B.id,
            fields.Date.to_date('2022-05-11'),
            wage=25000000,
            state='open')
        (cls.contract_B_01 | cls.contract_B_02).write({'personal_tax_rule_id': cls.tax_escalation.id})

        # """
        # Contract Advantages for 2 contracts.
        # Allowance on each contract is different
        # """
        advantages = cls.env['hr.advantage.template'].search(
            [('company_id', '=', cls.env.company.id),
             ('code', 'in', ADVANTAGE_CODE_LIST)])
        cls.contract_B_01.write({
            'advantage_ids': [(0, 0, {'template_id': advantages[1].id, 'amount': 500000}),  # PHONE
                              (0, 0, {'template_id': advantages[2].id, 'amount': 500000})]  # MEAL
        })

        cls.contract_B_02.write({
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 1000000}),  # TRAVEL
                              (0, 0, {'template_id': advantages[1].id, 'amount': 1000000}),  # PHONE
                              (0, 0, {'template_id': advantages[2].id, 'amount': 1000000}),  # MEAL
                              (0, 0, {'template_id': advantages[3].id, 'amount': 1000000}),  # RESPONSIBILITY
                              (0, 0, {'template_id': advantages[4].id, 'amount': 1000000}),  # HARDWORK
                              (0, 0, {'template_id': advantages[5].id, 'amount': 1000000}),  # PERFORMANCE
                              (0, 0, {'template_id': advantages[6].id, 'amount': 1000000})]  # HARMFUL
        })

        # """
        # Payoll Contribution Register
        #     wage base = 15.000.000
        #     employee_contrib_rate = 1%
        #     company_contrib_rate = 2%
        #
        # => Amount per month:
        #     Employee = 150.000
        #     Company = 300.000
        # """
        cls.contribute_types = cls.env['hr.payroll.contribution.type'].search([('company_id', '=', cls.env.company.id)])
        cls.contribute_types.write({
            'employee_contrib_rate': 1.0,
            'company_contrib_rate': 2.0,
        })
        cls.contract_B_01.write({
            'payroll_contribution_type_ids': cls.contribute_types
        })
        cls.contract_B_01.generate_payroll_contribution_registers()
        cls.contract_B_02.write({
            'payroll_contribution_type_ids': cls.contribute_types
        })
        cls.contribute_registers = cls.contract_B_01.payroll_contribution_register_ids
        cls.contribute_registers.action_confirm()

    def test_multi_tax_rules_01(self):
        """
        the payslip has 2 contract, 2 contracts has 1 tax rule

        => is_different_tax_rule = False
        """

        payslip = self.create_payslip(
            self.employee_B.id,
            fields.Date.to_date('2022-05-01'),
            fields.Date.to_date('2022-05-31'))

        self.assertRecordValues(
            payslip,
            [{
                'contracts_count': 2,
                'is_different_tax_rule': False
            }])

    def test_multi_tax_rules_02(self):
        """
        the payslip has 2 contract, 2 contracts has 2 tax rules

        => is_different_tax_rule = True
        """
        payslip = self.create_payslip(
            self.employee_B.id,
            fields.Date.to_date('2022-02-01'),
            fields.Date.to_date('2022-03-31'))

        self.assertRecordValues(
            payslip,
            [{
                'contracts_count': 2,
                'is_different_tax_rule': True
            }])

    def test_multi_contracts_01(self):
        """
        Input: create the payslip has 2 contracts with:
            same company
            same job
            same department
            same salary strcuture

        Output: create success
        """
        contracts = self.contract_B_01 | self.contract_B_02
        contracts.write({
            'job_id': self.job_product_dev.id,
            'department_id': self.product_department.id,
            'struct_id': self.structure_base.id,
        })

        self.create_payslip(
            self.employee_B.id,
            fields.Date.to_date('2022-05-01'),
            fields.Date.to_date('2022-05-31'))

    def test_multi_contracts_02(self):
        """
        Input: create the payslip has 2 contracts with 2 companies
        Output: Exception
        """
        company_2 = self.env['res.company'].create({
            'name': 'Company 2',
            'currency_id': self.env.ref('base.VND').id
        })
        self.contract_B_02.company_id = company_2
        with self.assertRaises(ValidationError):
            self.create_payslip(
                self.employee_B.id,
                fields.Date.to_date('2022-05-01'),
                fields.Date.to_date('2022-05-31'))

    def test_multi_contracts_03(self):
        """
        Input: create the payslip has 2 contracts with 2 jobs
        Output: Exception
        """
        self.contract_B_01.job_id = self.job_product_dev
        self.contract_B_02.job_id = self.job_product_manager
        with self.assertRaises(ValidationError):
            self.create_payslip(
                self.employee_B.id,
                fields.Date.to_date('2022-05-01'),
                fields.Date.to_date('2022-05-31'))

    def test_multi_contracts_04(self):
        """
        Input: create the payslip has 2 contracts with 2 departments
        Output: Exception
        """
        department_2 = self.create_department('Departments')
        self.contract_B_01.department_id = department_2
        self.contract_B_02.department_id = self.product_department
        with self.assertRaises(ValidationError):
            self.create_payslip(
                self.employee_B.id,
                fields.Date.to_date('2022-05-01'),
                fields.Date.to_date('2022-05-31'))

    def test_multi_contracts_05(self):
        """
        Input: create the payslip has 2 contracts with 2 salary structures
        Output: Exception
        """
        struct_2 = self.env['hr.payroll.structure'].with_context(tracking_disable=True).create({
            'name': 'New Salary Structure',
            'code': 'NEWBASE'
        })
        self.contract_B_01.struct_id = struct_2
        with self.assertRaises(ValidationError):
            self.create_payslip(
                self.employee_B.id,
                fields.Date.to_date('2022-05-01'),
                fields.Date.to_date('2022-05-31'))
