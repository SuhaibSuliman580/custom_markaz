from unittest.mock import patch

from odoo import fields
from odoo.tests import tagged

from .common import TestPayrollCommon
MSG = 'Test Generate HR Payslips not ok'


@tagged('post_install', '-at_install')
class TestPayrollPayslipCron(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipCron, cls).setUpClass()

        # Set Null (if exists)
        cls.env['hr.payslip.run'].unlink()

        # Set Company
        cls.env.company.write({
            'payslips_auto_generation': True,
            'payslips_auto_generation_mode': 'batch_period',
            'payslips_auto_generation_day': 3
        })
        # Employee: valid contract
        cls.contract_open_emp_A.write({'payslips_auto_generation': True})

        # Employee: invalid contract
        cls.contract_close_manager = cls.create_contract(
            cls.product_dep_manager.id,
            fields.Date.to_date('2021-1-1'),
            fields.Date.to_date('2021-6-30'),
            'close')
        cls.contract_close_manager.write({'payslips_auto_generation': True})

        # cron
        cls.cron = cls.env.ref('to_hr_payroll.ir_cron_generate_payslips')

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    def test_01_cron_generate_payslips(self):
        """
        Test: Không tạo phiếu lương định kỳ khi công ty không thiết lập tạo tự động bảng lương
        Input: Không có công ty nào (đa công ty) được đánh dấu tạo phiếu lương tự động
        Output: Không tạo phiếu lương định kỳ
        """
        self.env['res.company'].with_context(active_test=False).search([]).write({
            'payslips_auto_generation': False
        })
        self.cron.method_direct_trigger()
        batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
        self.assertFalse(batch, MSG)

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-1'))
    def test_02_cron_generate_payslips(self):
        """
        Test: Không tạo phiếu lương định kỳ khi Ngày hiện tại < ngày thiết lập tạo phiếu tự động trên setting
        Input:
            Công ty được đánh dấu tạo phiếu lương tự động
            Ngày hiện tại < ngày thiết lập tạo phiếu tự động trên setting
        Output: Không tạo phiếu lương định kỳ
        """
        self.cron.method_direct_trigger()
        batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
        self.assertFalse(batch, MSG)

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    def test_03_cron_generate_payslips(self):
        """
        Test: Không tạo phiếu lương định kỳ khi không có hợp đồng nào đánh dấu tạo bảng lương tự động
        Input:
            Công ty được đánh dấu tạo phiếu lương tự động
            Ngày hiện tại >= ngày thiết lập tạo phiếu tự động trên setting
            Không có Hợp đồng nhân viên nào đánh dấu tạo tự động
        Output: Không tạo phiếu lương định kỳ
        """
        self.env['hr.contract'].search([('company_id', '=', self.env.company.id)]).write({
            'payslips_auto_generation': False
            })
        self.cron.method_direct_trigger()
        batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
        self.assertFalse(batch, MSG)

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    def test_04_cron_generate_payslips(self):
        """
        Test: Không tạo phiếu lương định kỳ khi không có hợp đồng nào còn thời hạn
        Input:
            Công ty được đánh dấu tạo phiếu lương tự động
            Ngày hiện tại >= ngày thiết lập tạo phiếu tự động trên setting
            Có Hợp đồng nhân viên đánh dấu tạo tự động, Nhưng hợp đồng đã hết thời hạn hiệu lực
        Output: Không tạo phiếu lương định kỳ
        """
        self.contract_open_emp_A.write({
            'date_end': fields.Date.to_date('2021-7-1')
            })
        self.cron.method_direct_trigger()
        batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
        self.assertFalse(batch, MSG)

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    def test_05_cron_generate_payslips(self):
        """
        Test: Không tạo phiếu lương định kỳ khi không có hợp đồng nào còn thời hạn
        Input:
            Công ty được đánh dấu tạo phiếu lương tự động
            Ngày hiện tại >= ngày thiết lập tạo phiếu tự động trên setting
            Đã có bảng lương nằm trong khoảng thời gian tạo các phiếu lương tự động
        Output: Không tạo phiếu lương định kỳ
        """
        PayslipRun = self.env['hr.payslip.run']
        batch_1 = PayslipRun.create({
            'name': 'Test 1',
            'date_start': fields.Date.to_date('2021-8-10'),
            'date_end': fields.Date.to_date('2021-8-20'),
            'company_id': self.env.company.id,
            'salary_cycle_id': self.env.company.salary_cycle_id.id,
            })

        self.cron.method_direct_trigger()
        batch = PayslipRun.search([('company_id', '=', self.env.company.id),
                                   ('id', '!=', batch_1.id)])  # OdooBot
        self.assertFalse(batch, MSG)

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    def test_06_cron_generate_payslips(self):
        """
        Test: Tạo bảng lương tự động vào đầu tháng, cuối tháng theo chu kỳ không lệch chuẩn
        Input:
            - Công ty được đánh dấu tạo phiếu lương tự động,
            - Ngày hiện tại >= ngày thiết lập tạo phiếu tự động trên setting,
            - Có Hợp đồng nhân viên đánh dấu tạo tự động, hợp đồng hợp lệ,
            - Không có bảng lương nằm trong khoảng thời gian tạo các phiếu lương tự động
            - Chu kỳ lương không lệch chuẩn
            - Công ty thiết lập chế độ Chu kỳ bảng lương
        Output:
            - Tạo bảng lương, gồm các phiếu lương của các nhân viên tương ứng với các hợp đồng hợp lệ,
            - Chu kỳ bảng lương và phiếu lương là ngày đầu tháng - cuối tháng của tháng trước
        """
        self.cron.method_direct_trigger()
        batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
        self.assertTrue(batch, MSG)
        self.assertEqual(batch.date_start, fields.Date.to_date('2021-8-1'), MSG)
        self.assertEqual(batch.date_end, fields.Date.to_date('2021-8-31'), MSG)
        payslips = batch.slip_ids

        payslip_employee_A = payslips.filtered(lambda r: r.employee_id == self.product_emp_A)
        self.assertTrue(payslip_employee_A, MSG)
        self.assertEqual(payslip_employee_A.date_from, fields.Date.to_date('2021-8-1'), MSG)
        self.assertEqual(payslip_employee_A.date_to, fields.Date.to_date('2021-8-31'), MSG)
        # more ...

        payslip_manager = payslips.filtered(lambda r: r.employee_id == self.contract_close_manager)
        self.assertFalse(payslip_manager, MSG)

    @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    def test_07_cron_generate_payslips(self):
        """
        Test: Tạo bảng lương tự động vào đầu tháng, cuối tháng theo chu kỳ không lệch chuẩn
        Input:
            - Công ty được đánh dấu tạo phiếu lương tự động,
            - Ngày hiện tại >= ngày thiết lập tạo phiếu tự động trên setting,
            - Có Hợp đồng nhân viên đánh dấu tạo tự động, hợp đồng hợp lệ,
            - Không có bảng lương nằm trong khoảng thời gian tạo các phiếu lương tự động
            - Chu kỳ lương không lệch chuẩn
            - Công ty thiết lập chế độ Thời hạn hợp đồng
        Output:
            - Tạo bảng lương, gồm các phiếu lương của các nhân viên tương ứng với các hợp đồng hợp lệ,
            - Chu kỳ bảng lương là ngày đầu tháng - cuối tháng của tháng trước
            - Chu kỳ phiếu lương là ngày đầu tháng -> đến ngày kết thúc hợp đồng,
                * nếu ngày kết thúc hợp đồng nằm trong chu kỳ bảng lương
        """
        self.contract_open_emp_A.write({'date_end': fields.Date.to_date('2021-8-15')})
        self.env.company.write({
            'payslips_auto_generation_mode': 'contract_period',
            })

        self.cron.method_direct_trigger()
        batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
        self.assertTrue(batch, MSG)
        self.assertEqual(batch.date_start, fields.Date.to_date('2021-8-1'), MSG)
        self.assertEqual(batch.date_end, fields.Date.to_date('2021-8-31'), MSG)
        payslips = batch.slip_ids

        payslip_employee_A = payslips.filtered(lambda r: r.employee_id == self.product_emp_A)
        self.assertTrue(payslip_employee_A, MSG)
        self.assertEqual(payslip_employee_A.date_from, fields.Date.to_date('2021-8-1'), MSG)
        self.assertEqual(payslip_employee_A.date_to, fields.Date.to_date('2021-8-15'), MSG)
        # more ...

        payslip_manager = payslips.filtered(lambda r: r.employee_id == self.contract_close_manager)
        self.assertFalse(payslip_manager, MSG)

    # # 17. Tự động tạo phiếu lương theo định kỳ
    # @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    # def test_8(self):
    #     """
    #     Case 2: Công ty được đánh dấu tạo phiếu lương tự động, Ngày hiện tại >= ngày thiết lập tạo phiếu tự động trên setting
    #         Case 2.5:  Có Hợp đồng nhân viên đánh dấu tạo tự động, hợp đồng hợp lệ,
    #                     Không có bảng lương nằm trong khoảng thời gian tạo các phiếu lương tự động
    #                     Chu kỳ lương lệch chuẩn: lệch  -5 ngày, 0 tháng
    #                     Công ty thiết lập chế độ Thời hạn hợp đồng
    #             OUtput: Tạo bảng lương, gồm các phiếu lương của các nhân viên tương ứng với các hợp đồng hợp lệ,
    #                     Chu kỳ bảng lương là ngày đầu tháng - cuối tháng của tháng trước trừ đi lệch 5 ngày
    #                     Chu kỳ phiếu lương là ngày đầu tháng -> đến ngày kết thúc hợp đồng, trừ đi lệch 5 ngày
    #                         * nếu ngày kết thúc hợp đồng nằm trong chu kỳ bảng lương
    #     """
    #     self.contract_open_emp_A.write({'date_end': fields.Date.to_date('2021-8-15')})
    #     self.env.company.write({
    #         'payslips_auto_generation_mode': 'contract_period',
    #         })
    #     self.env.company.salary_cycle_id.write({
    #         'start_day_offset': -5,
    #         })
    #
    #     self.cron.method_direct_trigger()
    #     batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
    #     self.assertTrue(batch, MSG)
    #     self.assertEqual(batch.date_start, fields.Date.to_date('2021-7-27'), MSG)
    #     self.assertEqual(batch.date_end, fields.Date.to_date('2021-8-26'), MSG)
    #     payslips = batch.slip_ids
    #
    #     payslip_employee_A = payslips.filtered(lambda r: r.employee_id == self.product_emp_A)
    #     self.assertTrue(payslip_employee_A, MSG)
    #     self.assertEqual(payslip_employee_A.date_from, fields.Date.to_date('2021-7-27'), MSG)
    #     self.assertEqual(payslip_employee_A.date_to, fields.Date.to_date('2021-8-15'), MSG)
    #     # more ...
    #
    #     payslip_manager = payslips.filtered(lambda r: r.employee_id == self.contract_close_manager)
    #     self.assertFalse(payslip_manager, MSG)

    # # 17. Tự động tạo phiếu lương theo định kỳ
    # @patch.object(fields.Date, 'today', lambda: fields.Date.to_date('2021-9-4'))
    # def test_9(self):
    #     """
    #     Case 2: Công ty được đánh dấu tạo phiếu lương tự động, Ngày hiện tại >= ngày thiết lập tạo phiếu tự động trên setting
    #         Case 2.6:  Có Hợp đồng nhân viên đánh dấu tạo tự động, hợp đồng hợp lệ,
    #                     Không có bảng lương nằm trong khoảng thời gian tạo các phiếu lương tự động
    #                     Chu kỳ lương lệch chuẩn: lệch  -5 ngày, 0 tháng
    #                     Công ty thiết lập chế độ Chu kỳ bảng lương
    #             OUtput: Tạo bảng lương, gồm các phiếu lương của các nhân viên tương ứng với các hợp đồng hợp lệ,
    #                     Chu kỳ bảng lương và phiếu lương là ngày đầu tháng - cuối tháng của tháng trước trừ đi lệch 5 ngày
    #     """
    #     self.env.company.salary_cycle_id.write({
    #         'start_day_offset': -5,
    #         })
    #
    #     self.cron.method_direct_trigger()
    #     batch = self.env['hr.payslip.run'].search([('company_id', '=', self.env.company.id)])  # OdooBot
    #     self.assertTrue(batch, MSG)
    #     self.assertEqual(batch.date_start, fields.Date.to_date('2021-7-27'), MSG)
    #     self.assertEqual(batch.date_end, fields.Date.to_date('2021-8-26'), MSG)
    #     payslips = batch.slip_ids
    #
    #     payslip_employee_A = payslips.filtered(lambda r: r.employee_id == self.product_emp_A)
    #     self.assertTrue(payslip_employee_A, MSG)
    #     self.assertEqual(payslip_employee_A.date_from, fields.Date.to_date('2021-7-27'), MSG)
    #     self.assertEqual(payslip_employee_A.date_to, fields.Date.to_date('2021-8-26'), MSG)
    #     # more ...
    #
    #     payslip_manager = payslips.filtered(lambda r: r.employee_id == self.contract_close_manager)
    #     self.assertFalse(payslip_manager, MSG)
