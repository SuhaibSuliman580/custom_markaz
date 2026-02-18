from odoo import fields
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollPayslipInputs(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipInputs, cls).setUpClass()

        Category = cls.env['hr.salary.rule.category']
        category_1 = Category.search([('company_id', '=', cls.env.company.id), ('code', '=', 'DED_BEFORE_TAX')], limit=1)
        category_2 = Category.search([('company_id', '=', cls.env.company.id), ('code', '=', 'PERFORMANCE')], limit=1)

        # input rules
        cls.input_salary_commission = cls.env['hr.salary.rule'].with_context(tracking_disable=True).create({
            'name': 'Commission',
            'code': 'COMMISSION',
            'sequence': 590,
            'struct_id': cls.structure_base.id,
            'category_id': category_2.id,
            'condition_select': 'python',
            'condition_python': "result = inputs.COMMISSION and inputs.COMMISSION.amount != 0",
            'amount_select': 'code',
            'amount_python_compute': "result = inputs.COMMISSION.amount",
            'input_salary': True
        })
        cls.input_salary_fine = cls.env['hr.salary.rule'].with_context(tracking_disable=True).create({
            'name': 'Fine',
            'code': 'FINE',
            'sequence': 4250,
            'struct_id': cls.structure_base.id,
            'category_id': category_1.id,
            'condition_select': 'python',
            'condition_python': "result = inputs.FINE and inputs.FINE.amount != 0",
            'amount_select': 'code',
            'amount_python_compute': "result = inputs.FINE.amount",
            'input_salary': True
        })

    def test_01_input_rules_on_payslip(self):
        """
        input rules appear on the payslip
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-07-01'),
            fields.Date.to_date('2021-07-31'))
        self.assertRecordValues(
            payslip.input_line_ids,
            [{
                'salary_rule_id': self.input_salary_commission.id,
                'amount': 0.0,
            },
            {
                'salary_rule_id': self.input_salary_fine.id,
                'amount': 0.0,
            }])

    def test_02_input_rules_on_payslip_lines(self):
        """
        input rules appear on  payslip lines

        1. if the amount of the input rule ! = 0, appear payslip lines with the same code
        2. if the amount of the input rule = 0, does not appear on payslip line
        """
        payslip = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-07-01'),
            fields.Date.to_date('2021-07-31'))
        payslip.input_line_ids.filtered(lambda r: r.salary_rule_id == self.input_salary_commission).write({
            'amount': 600000
        })
        payslip.compute_sheet()

        # 2.
        fine_payslip_line = payslip.line_ids.filtered(lambda r: r.salary_rule_id == self.input_salary_fine)
        self.assertFalse(fine_payslip_line)

        # 1.
        commission_payslip_line = payslip.line_ids.filtered(lambda r: r.salary_rule_id == self.input_salary_commission)
        self.assertRecordValues(
            commission_payslip_line,
            [{
                'name': 'Commission',
                'code': 'COMMISSION',
                'amount': 600000,
            }])
