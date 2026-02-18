from odoo import fields
from odoo.tests import tagged
from odoo.tools.float_utils import float_round

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollPayslipReport(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipReport, cls).setUpClass()
        # Prepare data
        cls.contract_manager = cls.create_contract(cls.product_dep_manager.id,
                                                   fields.Date.to_date('2021-1-1'),
                                                   fields.Date.to_date('2021-12-31'),
                                                   'open', wage=35000000)
        advantages = cls.env['hr.advantage.template'].search([('company_id', '=', cls.env.company.id)])
        types = cls.env['hr.payroll.contribution.type'].search([('company_id', '=', cls.env.company.id)])
        types[0].write({'employee_contrib_rate': 1, 'company_contrib_rate': 2})
        types[1].write({'employee_contrib_rate': 2, 'company_contrib_rate': 4})
        types[2].write({'employee_contrib_rate': 2.5, 'company_contrib_rate': 5})
        types[3].write({'employee_contrib_rate': 5, 'company_contrib_rate': 10})
        contracts = cls.contract_open_emp_A + cls.contract_manager
        contracts.write({
            'advantage_ids': [(0, 0, {'template_id': advantages[0].id, 'amount': 100000}),
                              (0, 0, {'template_id': advantages[1].id, 'amount': 200000}),
                              (0, 0, {'template_id': advantages[2].id, 'amount': 300000}),
                              (0, 0, {'template_id': advantages[3].id, 'amount': 400000}),
                              (0, 0, {'template_id': advantages[4].id, 'amount': 500000}),
                              (0, 0, {'template_id': advantages[5].id, 'amount': 600000}),
                              (0, 0, {'template_id': advantages[6].id, 'amount': 700000})],
            'payroll_contribution_type_ids': [(6, 0, types.ids)]
        })
        contracts.generate_payroll_contribution_registers()
        contracts.payroll_contribution_register_ids.action_confirm()
        cls.generate_work_entry(
            contracts,
            fields.Datetime.to_datetime('2021-07-01 00:00:00'),
            fields.Datetime.to_datetime('2021-09-30 23:59:59'))

        # payslip: Draft
        cls.payslip_1 = cls.create_payslip(cls.product_emp_A.id,
                                           fields.Date.to_date('2021-9-1'),
                                           fields.Date.to_date('2021-9-30'))

        # payslip: Draft + Compute Sheet
        cls.payslip_2 = cls.create_payslip(cls.product_emp_A.id,
                                           fields.Date.to_date('2021-9-1'),
                                           fields.Date.to_date('2021-9-30'))
        cls.payslip_2.compute_sheet()

        # payslip: Cancel
        cls.payslip_3 = cls.create_payslip(cls.product_emp_A.id,
                                           fields.Date.to_date('2021-9-1'),
                                           fields.Date.to_date('2021-9-30'))
        cls.payslip_3.action_payslip_verify()
        cls.payslip_3.action_payslip_cancel()

        # payslip: Verified
        cls.payslip_4 = cls.create_payslip(cls.product_emp_A.id,
                                           fields.Date.to_date('2021-8-1'),
                                           fields.Date.to_date('2021-8-31'))
        cls.payslip_4.action_payslip_verify()

        # payslip: Done
        cls.payslip_5 = cls.create_payslip(cls.product_emp_A.id,
                                           fields.Date.to_date('2021-7-1'),
                                           fields.Date.to_date('2021-7-31'))
        cls.payslip_5.action_payslip_verify()
        cls.payslip_5.action_payslip_done()

        # payslip: Draft
        cls.payslip_6 = cls.create_payslip(cls.product_dep_manager.id,
                                           fields.Date.to_date('2021-9-1'),
                                           fields.Date.to_date('2021-9-30'))

        # payslip: Draft + Compute Sheet
        cls.payslip_7 = cls.create_payslip(cls.product_dep_manager.id,
                                           fields.Date.to_date('2021-9-1'),
                                           fields.Date.to_date('2021-9-30'))
        cls.payslip_7.compute_sheet()

        # payslip: Cancel
        cls.payslip_8 = cls.create_payslip(cls.product_dep_manager.id,
                                           fields.Date.to_date('2021-9-1'),
                                           fields.Date.to_date('2021-9-30'))
        cls.payslip_8.action_payslip_verify()
        cls.payslip_8.action_payslip_cancel()

        # payslip: Verified
        cls.payslip_9 = cls.create_payslip(cls.product_dep_manager.id,
                                           fields.Date.to_date('2021-8-1'),
                                           fields.Date.to_date('2021-8-31'))
        cls.payslip_9.action_payslip_verify()

        # payslip: Done
        cls.payslip_10 = cls.create_payslip(cls.product_dep_manager.id,
                                            fields.Date.to_date('2021-7-1'),
                                            fields.Date.to_date('2021-7-31'))
        cls.payslip_10.action_payslip_verify()
        cls.payslip_10.action_payslip_done()

        cls.payslips_emp_A_in_report = cls.payslip_2 + cls.payslip_4 + cls.payslip_5
        cls.payslips_manager_in_report = cls.payslip_7 + cls.payslip_9 + cls.payslip_10
        cls.payslips_in_tax_report = cls.payslips_emp_A_in_report + cls.payslips_manager_in_report

    def test_salary_report(self):
        """
        16.1: Phân tích lương
        """
        salary_reports = self.env['hr.payroll.analysis'].search([('company_id', '=', self.env.company.id)])

        # check payslips in report
        emp_A_salary_reports = salary_reports.filtered(lambda r: r.employee_id == self.product_emp_A)
        manager_salary_reports = salary_reports.filtered(lambda r: r.employee_id == self.product_dep_manager)
        self.assertEqual(self.payslips_emp_A_in_report, emp_A_salary_reports.slip_id, 'Test Payroll Analysis (Payslips) not ok')
        self.assertEqual(self.payslips_manager_in_report, manager_salary_reports.slip_id, 'Test Payroll Analysis (Payslips) not ok')

        # check payslip lines in report
        self.assertTrue(self.payslips_in_tax_report.line_ids, 'Test Payroll Analysis (Payslip Lines) not ok')

        # check detail
        for line in salary_reports:
            ps = line.slip_id
            ps_line = ps.line_ids.filtered(lambda r: r.id == line.id)
            self.assertRecordValues(line, [{
                'date_create': ps.create_date,
                'date_from': ps.date_from,
                'date_to': ps.date_to,
                'state': ps.state,
                'date_confirmed': ps.date_confirmed,
                'job_id': ps.job_id.id,
                'struct_id': ps.struct_id.id,
                'employee_id': ps_line.employee_id.id,
                'amount': ps_line.total,
                'register_id': ps_line.register_id.id,
                'category_id': ps_line.category_id.id,
                'salary_rule_id': ps_line.salary_rule_id.id,
                'salary_rule_name': ps_line.salary_rule_id.name,
                'rule_appears_on_payslip': ps_line.salary_rule_id.appears_on_payslip,
                'contribution_register_category_id': ps_line.salary_rule_id.register_category_id.id
            }])
            if ps.department_id:
                self.assertEqual(line.department_id, ps.department_id, 'Test Payroll Analysis (register_id) not ok')
            else:
                self.assertEqual(line.department_id, ps.employee_id.department_id, 'Test Payroll Analysis (register_id) not ok')
            if ps_line.category_id.paid_by_company:
                self.assertEqual(line.company_cost, ps_line.total, 'Test Payroll Analysis (register_id) not ok')
            else:
                self.assertEqual(line.company_cost, 0, 'Test Payroll Analysis (register_id) not ok')

    def test_tax_report(self):
        """
        16.4 Phân tích thuế thu nhập cá nhân
        """
        tax_reports = self.env['payslip.personal.income.tax.analysis'].search([('company_id', '=', self.env.company.id)])
        emp_A_tax_reports = tax_reports.filtered(lambda r: r.employee_id == self.product_emp_A)
        manager_tax_reports = tax_reports.filtered(lambda r: r.employee_id == self.product_dep_manager)

        # check payslips in tax report
        self.assertEqual(tax_reports.slip_id, self.payslips_in_tax_report, 'Test Payslip Personal Income Tax Analysis not ok')
        self.assertEqual(emp_A_tax_reports.slip_id, self.payslips_emp_A_in_report, 'Test Payslip Personal Income Tax Analysis not ok')
        self.assertEqual(manager_tax_reports.slip_id, self.payslips_manager_in_report, 'Test Payslip Personal Income Tax Analysis not ok')

        # check tax amount
        emp_A_tax_amount_report = sum(emp_A_tax_reports.mapped('tax_amount'))
        emp_A_tax_amount = sum(self.payslips_emp_A_in_report.payslip_personal_income_tax_ids.mapped('tax_amount'))
        self.assertEqual(emp_A_tax_amount_report, emp_A_tax_amount,
                         'Test Payslip Personal Income Tax Analysis (Tax amount) not ok')

        manager_tax_amount_report = sum(manager_tax_reports.mapped('tax_amount'))
        manager_tax_amount = sum(self.payslips_manager_in_report.payslip_personal_income_tax_ids.mapped('tax_amount'))
        self.assertEqual(manager_tax_amount_report, manager_tax_amount,
                         'Test Payslip Personal Income Tax Analysis (Tax amount) not ok')

        # check state
        # verified : payslip state is verify/done
        state_verified = self.payslip_4 + self.payslip_5 + self.payslip_9 + self.payslip_10
        state_verified_report = tax_reports.filtered(lambda r: r.state == 'verified').slip_id
        self.assertEqual(state_verified, state_verified_report, 'Test Payslip Personal Income Tax Analysis (state) not ok')
        # draft: payslip lines and payslip state not in (verify/done/cancel)
        state_draft = self.payslip_2 + self.payslip_7
        state_draft_report = tax_reports.filtered(lambda r: r.state == 'draft').slip_id
        self.assertEqual(state_draft, state_draft_report, 'Test Payslip Personal Income Tax Analysis (State) not ok')

        # check detail
        for line in tax_reports:
            ps = line.slip_id
            ps_income_line = ps.payslip_personal_income_tax_ids.filtered(lambda r: r.id == line.id)

            self.assertRecordValues(line, [{
                'date': ps.date_to,
                'gross_salary': ps.gross_salary,
                'base': ps_income_line.base,
                'upper_base': ps_income_line.upper_base,
                'tax_amount': ps_income_line.tax_amount,
                'personal_tax_rule_id': ps_income_line.personal_tax_rule_id.id,
            }])
            amount = float_round((line.tax_amount / ps.gross_salary) * 100, precision_digits=2)
            self.assertEqual(float_round(line.rate, precision_digits=2), amount, 'Test Payslip Personal Income Tax Analysis (rate) not ok')
