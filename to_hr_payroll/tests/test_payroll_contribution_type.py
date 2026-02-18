from psycopg2 import IntegrityError

from odoo import fields
from odoo.tools import mute_logger
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollContributionType(TestPayrollCommon):

    def create_wizard_change_rate(self, payroll_contribution_reg_ids, employee_contrib_rate, company_contrib_rate, date):
        return self.env['hr.payroll.contrib.action.change.rates'].create({
            'payroll_contribution_reg_ids': payroll_contribution_reg_ids.ids,
            'employee_contrib_rate': employee_contrib_rate,
            'company_contrib_rate': company_contrib_rate,
            'date': date
        })

    def test_01_contribution_type_unique_code_1(self):
        """
        Test: Trường Mã của Kiểu Đăng ký đóng góp từ lương phải là duy nhất tương ứng với 1 công ty
        Input: Tạo Khác mã => tạo thành công
        """
        register = self.env['hr.contribution.register'].search([('company_id', '=', self.env.company.id)], limit=1)
        contribution_type = self.env['hr.payroll.contribution.type'].create({
            'name': 'Type 1',
            'code': 'TT1',
            'employee_contrib_reg_id': register.id,
            'employee_contrib_rate': 1,
            'company_id': self.env.company.id
        })
        self.assertTrue(contribution_type, 'Test create payroll contribution type not ok')

    def test_01_contribution_type_unique_code_2(self):
        """
        Test: Trường Mã của Kiểu Đăng ký đóng góp từ lương phải là duy nhất tương ứng với 1 công ty
        Input: Cùng mã, khác công ty => Tạo thành công
        """
        ContributionType = self.env['hr.payroll.contribution.type']
        register = self.env['hr.contribution.register'].search([('company_id', '=', self.env.company.id)], limit=1)
        self.env['hr.payroll.contribution.type'].create({
            'name': 'Type 1',
            'code': 'TT1',
            'employee_contrib_reg_id': register.id,
            'employee_contrib_rate': 1,
            'company_id': self.env.company.id
        })

        company2 = self.env['res.company'].create({'name': 'CTY 2'})
        contribution_type = ContributionType.create({
            'name': 'Type 1',
            'code': 'TT1',
            'employee_contrib_reg_id': register.id,
            'employee_contrib_rate': 1,
            'company_id': company2.id
            })
        self.assertTrue(contribution_type, 'Test create payroll contribution type not ok')

    @mute_logger('odoo.sql_db')
    def test_01_contribution_type_unique_code_3(self):
        """
        Test: Trường Mã của Kiểu Đăng ký đóng góp từ lương phải là duy nhất tương ứng với 1 công ty
        Input: Cùng mã, cùng công ty => Tạo không thành công
        """
        register = self.env['hr.contribution.register'].search([('company_id', '=', self.env.company.id)], limit=1)
        ContributionType = self.env['hr.payroll.contribution.type']
        ContributionType.create({
            'name': 'Type 1',
            'code': 'TT1',
            'employee_contrib_reg_id': register.id,
            'employee_contrib_rate': 1,
            'company_id': self.env.company.id
            })

        with self.assertRaises(IntegrityError):
            ContributionType.create({
                'name': 'Type 2',
                'code': 'TT1',
                'employee_contrib_reg_id': register.id,
                'employee_contrib_rate': 1,
                'company_id': self.env.company.id
            })

    def test_02_contribution_type_mass_change_rate_1(self):
        """
        Test: Nút "Mass Change Rates" trên Kiểu Đăng ký đóng góp từ lương
        Input:
            1. Nhấn nút "Mass Change Rates"
                => Hiển thị form nhập thông tin thay đổi: ngày, tỷ lệ đóng góp của nhân viên, công ty
            2. Nhấn nút "Mass Change Rates" -> Xác nhận thay đổi
                (đăng ký đống góp liên quan ở 6 trạng thái khác nhau)
        Output:
            1. Hiển thị form nhập thông tin thay đổi: ngày, tỷ lệ đóng góp của nhân viên, công ty
            2.  - Tất cả các đăng ký đóng góp từ lương liên quan đến loại này ở trạng thái "Đã xác nhận" / "Tái tham gia"  sẽ thay đổi tỷ lệ đóng góp của nhân viên và công ty
                - Khi các đănng ký đóng góp từ lương này được thay đổi thì sẽ tạo ra các bản ghi lịch sử thay đổi đóng góp từ lương
                - Kiểu đăng ký đóng góp sẽ không thay đổi tỷ lệ đóng góp
        """
        contrib_type = self.env['hr.payroll.contribution.type'].search([('company_id', '=', self.env.company.id)], limit=1)
        contrib_type.current_payroll_contribution_reg_ids.action_cancel()
        register_1 = self.create_contrib_register(self.product_emp_A, contrib_type, state="draft")

        # 1. Test button "Mass Change Rates"
        wizard_id = self.env.ref('to_hr_payroll.hr_payroll_contrib_action_change_rates_action').id
        result = contrib_type.action_mass_change_rates()
        self.assertEqual(wizard_id, result.get('id', False), "Test Wizard display: Change Contribution Rates not ok.")

        # 2. Test button "Mass Change Rates", Process change
        # case 1: State: Draft
        wizard_change_rate = self.create_wizard_change_rate(
            contrib_type.current_payroll_contribution_reg_ids,
            1, 2,
            fields.Date.today())
        wizard_change_rate.process()

        self.assertNotEqual(register_1.employee_contrib_rate, 1, 'Test Change Contribution Rates (with Draft state) not ok')
        self.assertNotEqual(register_1.company_contrib_rate, 2, 'Test Change Contribution Rates (with Draft state) not ok')
        self.assertFalse(register_1.payroll_contribution_history_ids, 'Test Change Contribution Rates (with Draft state) not ok')

        # case 2: State: Confirmed
        register_1.action_confirm()
        wizard_change_rate = self.create_wizard_change_rate(
            contrib_type.current_payroll_contribution_reg_ids,
            1, 2,
            fields.Date.to_date('2021-3-1'))
        wizard_change_rate.process()

        self.assertEqual(register_1.employee_contrib_rate, 1, 'Test Change Contribution Rates (with Confirmed state) not ok')
        self.assertEqual(register_1.company_contrib_rate, 2, 'Test Change Contribution Rates (with Confirmed state) not ok')
        self.assertEqual(
            register_1.payroll_contribution_history_ids[-1].date_from,
            fields.Date.to_date('2021-3-1'),
            'Test Change Contribution Rates (with Confirmed state) not ok')
        self.assertEqual(
            register_1.payroll_contribution_history_ids[-2].date_to,
            fields.Date.to_date('2021-2-28'),
            'Test Change Contribution Rates (with Confirmed state) not ok')

        # case 3: State: Suspended
        register_1.write({'date_suspended': fields.Date.to_date('2021-4-1')})
        register_1.with_context(call_wizard=False).action_suspend()
        wizard_change_rate = self.create_wizard_change_rate(
            contrib_type.current_payroll_contribution_reg_ids,
            3, 4,
            fields.Date.to_date('2021-5-1'))
        wizard_change_rate.process()

        self.assertNotEqual(register_1.employee_contrib_rate, 3, 'Test Change Contribution Rates (with suspended state) not ok')
        self.assertNotEqual(register_1.company_contrib_rate, 4, 'Test Change Contribution Rates (with suspended state) not ok')

        # case 4: State: Resumed
        register_1.write({'date_resumed': fields.Date.to_date('2021-4-30')})
        register_1.with_context(call_wizard=False).action_resume()
        wizard_change_rate = self.create_wizard_change_rate(
            contrib_type.current_payroll_contribution_reg_ids,
            3, 4,
            fields.Date.to_date('2021-5-1'))
        wizard_change_rate.process()

        self.assertEqual(register_1.employee_contrib_rate, 3, 'Test Change Contribution Rates (with resumed state) not ok')
        self.assertEqual(register_1.company_contrib_rate, 4, 'Test Change Contribution Rates (with resumed state) not ok')
        self.assertEqual(
            register_1.payroll_contribution_history_ids[-1].date_from,
            fields.Date.to_date('2021-5-1'),
            'Test Change Contribution Rates (with resumed state) not ok')

        # case 5: State: Done
        register_1.write({'date_to': fields.Date.to_date('2021-5-31')})
        register_1.with_context(call_wizard=False).action_done()
        wizard_change_rate = self.create_wizard_change_rate(
            contrib_type.current_payroll_contribution_reg_ids,
            5, 6,
            fields.Date.to_date('2021-5-1'))

        wizard_change_rate.process()
        self.assertNotEqual(register_1.employee_contrib_rate, 5, 'Test Change Contribution Rates (with Done state) not ok')
        self.assertNotEqual(register_1.company_contrib_rate, 6, 'Test Change Contribution Rates (with Done state) not ok')

        # case 6: State: Cancelled
        register_1.action_cancel()
        wizard_change_rate = self.create_wizard_change_rate(
            contrib_type.current_payroll_contribution_reg_ids,
            5, 6,
            fields.Date.to_date('2021-5-1'))
        wizard_change_rate.process()

        self.assertNotEqual(register_1.employee_contrib_rate, 5,
                            'Test Change Contribution Rates (with Cancelled state) not ok')
        self.assertNotEqual(register_1.company_contrib_rate, 6,
                            'Test Change Contribution Rates (with Cancelled state) not ok')
