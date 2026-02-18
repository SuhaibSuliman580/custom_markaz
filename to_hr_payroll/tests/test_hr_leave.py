from datetime import datetime

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestHRLeave(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestHRLeave, cls).setUpClass()

        cls.leave_type = cls.env['hr.leave.type'].search([('unpaid', '=', True)], limit=1)
        cls.leave_type.write({'request_unit': 'day'})

    def test_adjust_dates_1(self):
        """
        Điều chỉnh ngày kết thúc trùng với ngày kết thúc muộn nhất của phiếu lương nằm trong khoảng xin nghỉ
            Input:
                Nghỉ tháng 7+8 (5/7 - 31/8)
                Tạo phiếu lương tháng 7 (1/7 - 31/7)
                Điều chỉnh ngày kết thúc xin nghỉ về 31/7
            Output:
                Điều chỉnh ngày kết thúc thành công, tính lại ngày ,giờ nghỉ
                Phiếu lương không bị ảnh hưởng
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 7, 5, 6, 0),
            datetime(2021, 8, 31, 15, 0))
        leave.action_validate()
        self.env['hr.work.entry'].search([('leave_id', '=', leave.id)]).state = 'validated'

        # payslip: 1/7/2021 - 31/7-2021
        payslip = self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-07-01'),
            fields.Date.to_date('2021-07-31'))

        self.assertRecordValues(payslip, [{
            'worked_days': 2,
            'worked_hours': 16,
            'leave_days': 20,
            'leave_hours': 160,
        }])

        wizard = self.env['adjustment.leave'].create({
            'leave_id': leave.id,
            'date_from': fields.Date.to_date('2021-07-05'),
            'date_to': fields.Date.to_date('2021-07-31')
        })
        wizard.action_confirm()
        self.assertRecordValues(leave, [{
            'date_from': datetime(2021, 7, 5, 6, 0),
            'date_to': datetime(2021, 7, 31, 15, 0),
            'number_of_days': 20,
            'number_of_days_display': 20,
            'number_of_hours_display': 160
        }])
        self.assertRecordValues(payslip, [{
            'worked_days': 2,
            'worked_hours': 16,
            'leave_days': 20,
            'leave_hours': 160,
        }])

    def test_adjust_dates_2(self):
        """
        Điều chỉnh ngày kết thúc lớn hơn ngày kết thúc muộn nhất của phiếu lương nằm trong khoảng xin nghỉ
            Input:
                Nghỉ từ 23/5 - 23/11
                Tạo phiếu lương tháng 5 (1/5 - 31/5)
                Điều chỉnh ngày kết thúc xin nghỉ về 6/10
            Output:
                Điều chỉnh ngày kết thúc thành công, tính lại ngày ,giờ nghỉ
                Phiếu lương không bị ảnh hưởng
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 5, 23, 6, 0),
            datetime(2021, 11, 23, 15, 0))
        leave.action_validate()
        self.env['hr.work.entry'].search([('leave_id', '=', leave.id)]).state = 'validated'

        # payslip: 1/5/2021 - 31/5-2021
        payslip = self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-05-01'),
            fields.Date.to_date('2021-05-31'))

        wizard = self.env['adjustment.leave'].create({
            'leave_id': leave.id,
            'date_from': fields.Date.to_date('2021-05-23'),
            'date_to': fields.Date.to_date('2021-10-6')
        })
        wizard.action_confirm()
        self.assertRecordValues(leave, [{
            'date_from': datetime(2021, 5, 23, 6, 0),
            'date_to': datetime(2021, 10, 6, 15, 0),
            # Tháng 5: 6d - 48h
            # Tháng 6: 22d - 176h
            # tháng 7: 22d - 176h
            # tháng 8: 22d - 176h
            # tháng 9: 22d - 176h
            # tháng 10: 4d - 32h
            'number_of_days': 98,
            'number_of_days_display': 98,
            'number_of_hours_display': 784
        }])
        self.assertRecordValues(payslip, [{
            'worked_days': 15,
            'worked_hours': 120,
            'leave_days': 6,
            'leave_hours': 48,
        }])

    def test_adjust_dates_3(self):
        """
        Điều chỉnh ngày kết thúc nhỏ hơn ngày kết thúc muộn nhất của phiếu lương nằm trong khoảng xin nghỉ
            Input:
                Nghỉ tháng 7+8 (5/7 - 31/8)
                Tạo phiếu lương tháng 7 (1/7 - 31/7)
                Điều chỉnh ngày kết thúc xin nghỉ về 29/7
            Output: không thành công
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 7, 5, 6, 0),
            datetime(2021, 8, 31, 15, 0))
        leave.action_validate()

        # payslip: 1/7/2021 - 31/7-2021
        self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-07-01'),
            fields.Date.to_date('2021-07-31'))

        wizard = self.env['adjustment.leave'].create({
            'leave_id': leave.id,
            'date_from': fields.Date.to_date('2021-07-05'),
            'date_to': fields.Date.to_date('2021-07-29')
        })
        self.assertRaises(UserError, wizard.action_confirm)

    def test_adjust_dates_4(self):
        """
        Điều chỉnh lại ngày kết thúc của xin nghỉ có ngày kết thúc đã nằm trong phiếu lương
            Input:
                Nghỉ từ 5/7 - 15/7
                Tạo phiếu lương tháng 7 (1/7 - 31/7)
                Điều chỉnh ngày kết thúc xin nghỉ
            Output: không thành công
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 7, 5, 6, 0),
            datetime(2021, 7, 15, 15, 0))
        leave.action_validate()

        # payslip: 1/7/2021 - 31/7-2021
        self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-07-01'),
            fields.Date.to_date('2021-07-31'))

        wizard = self.env['adjustment.leave'].create({
            'leave_id': leave.id,
            'date_from': fields.Date.to_date('2021-07-05'),
            'date_to': fields.Date.to_date('2021-07-20')
        })
        self.assertRaises(UserError, wizard.action_confirm)

    def test_adjust_dates_5(self):
        """
        Điều chỉnh lại ngày bắt đầu của xin nghỉ vào khoảng thời gian của phiếu lương
            Input:
                Nghỉ từ  5/7 - 15/7
                Tạo phiếu lương tháng 6 (1/6 - 30/6)
                Điều chỉnh ngày bắt đầu từ 5/7 về 25/6 và 25/5
            Output: không thành công
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 7, 5, 6, 0),
            datetime(2021, 7, 15, 15, 0))
        leave.action_validate()

        # payslip: 1/7/2021 - 31/7-2021
        self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-06-01'),
            fields.Date.to_date('2021-06-30'))

        wizard = self.env['adjustment.leave'].create({
            'leave_id': leave.id,
            'date_from': fields.Date.to_date('2021-06-25'),
            'date_to': fields.Date.to_date('2021-07-15')
        })
        self.assertRaises(UserError, wizard.action_confirm)

        wizard.write({
            'date_from': fields.Date.to_date('2021-5-25')
        })
        self.assertRaises(UserError, wizard.action_confirm)

    def test_adjust_dates_6(self):
        """
        Điều chỉnh lại ngày kết thúc của xin nghỉ vào khoảng thời gian của phiếu lương
            Input:
                Nghỉ từ  5/7 - 15/7
                Tạo phiếu lương tháng 8 (1/8 - 31/8)
                Điều chỉnh ngày kết thúc từ 15/7 về 25/8 và 25/9
            Output: không thành công
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 7, 5, 6, 0),
            datetime(2021, 7, 15, 15, 0))
        leave.action_validate()

        # payslip: 1/7/2021 - 31/7-2021
        self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-08-01'),
            fields.Date.to_date('2021-08-30'))

        wizard = self.env['adjustment.leave'].create({
            'leave_id': leave.id,
            'date_from': fields.Date.to_date('2021-07-05'),
            'date_to': fields.Date.to_date('2021-8-25')
        })
        self.assertRaises(UserError, wizard.action_confirm)

        wizard.write({
            'date_to': fields.Date.to_date('2021-09-25')
        })
        self.assertRaises(UserError, wizard.action_confirm)

    def test_adjust_dates_7(self):
        """
        Điều chỉnh lại ngày kết thúc của xin nghỉ vào khoảng thời gian của phiếu lương đã hủy
            Input:
                Nghỉ từ  5/7 - 15/7
                Tạo phiếu lương tháng 8 (1/8 - 31/8) - đã hủy
                Điều chỉnh ngày kết thúc từ 15/7 về 25/8
            Output: Thành công, tính lại ngày, giờ xin nghỉ
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 7, 5, 6, 0),
            datetime(2021, 7, 15, 15, 0))
        leave.action_validate()

        # payslip: 1/7/2021 - 31/7-2021
        payslip = self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-08-01'),
            fields.Date.to_date('2021-08-30'))
        payslip.action_payslip_verify()
        payslip.action_payslip_cancel()

        wizard = self.env['adjustment.leave'].create({
            'leave_id': leave.id,
            'date_from': fields.Date.to_date('2021-07-05'),
            'date_to': fields.Date.to_date('2021-8-25')
        })
        wizard.action_confirm()

        self.assertRecordValues(leave, [{
            'date_from': datetime(2021, 7, 5, 6, 0),
            'date_to': datetime(2021, 8, 25, 15, 0),
            'number_of_days': 38,
            'number_of_days_display': 38,
            'number_of_hours_display': 304
        }])

    def test_02_unlink_resource_leave(self):
        """
        Test: Cannot be deleted resource calendar leave if it is already related to another draft Payslip
        Input:
            - create a timeoff & validate it
            - create a payslip & confirm
            - delete resource calendar leave (of the timeoff)
        Ouput:
            Exception, Cannot be deleted resource calendar leave
        """
        leave = self.create_holiday(
            'Test Leave 1',
            self.product_emp_A.id,
            self.leave_type.id,
            datetime(2021, 8, 5, 6, 0),
            datetime(2021, 8, 15, 15, 0))
        leave.action_validate()
        work_entries = self.env['hr.work.entry'].sudo().search([('leave_id', '=', leave.id)])
        work_entries.action_validate_work_entry()

        payslip = self.create_payslip(self.product_emp_A.id,
            fields.Date.to_date('2021-08-01'),
            fields.Date.to_date('2021-08-30'))
        payslip.action_payslip_verify()

        resource_leave = self.env['resource.calendar.leaves'].search([('holiday_id', '=', leave.id)])
        with self.assertRaises(UserError):
            resource_leave.unlink()

    def test_payslip_timeoff(self):
        """
        Work/leave information of payslip recording time off with leave type is 'leave'
        Input:
            Timeoff Type 1: time_type field is 'leave'
            Timeoff Type 2: time_type field is 'other' and Work Entry type: is_leave = False
            Create timeoff with this 2 timeoff type
            Create the payslip
        Output:
            Work/leave information of payslip recording time off with leave type is 'leave'
        """
        work_entry_type = self.env['hr.work.entry.type'].create({
            'name': 'Work From Home 2',
            'code': 'WFH2',
            'is_leave': False
        })
        unpaid_type = self.env.ref('hr_holidays.holiday_status_unpaid')
        paid_type = self.env['hr.leave.type'].create({
            'name': 'Work From Home 2',
            'requires_allocation': 'no',
            'leave_validation_type': 'both',
            'time_type': 'other',
            'work_entry_type_id': work_entry_type.id
        })

        timeoff_1 = self.create_holiday(
            'Time off: 2021/07/06 - 2021/07/09',
            self.product_emp_A.id,
            unpaid_type.id,
            fields.Datetime.to_datetime('2021-07-06 06:00:00'),
            fields.Datetime.to_datetime('2021-07-09 15:00:00'),
        )
        timeoff_2 = self.create_holiday(
            'Time off: 2021/07/13 - 2021/07/16',
            self.product_emp_A.id,
            paid_type.id,
            fields.Datetime.to_datetime('2021-07-13 06:00:00'),
            fields.Datetime.to_datetime('2021-07-16 15:00:00'),
        )
        (timeoff_1 | timeoff_2).action_validate()
        work_entries = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.product_emp_A.id),
            ('date_start', '>=', datetime(2021, 7, 1, 6, 0)),
            ('date_stop', '<=', datetime(2021, 7, 31, 16, 0)),
        ])
        work_entries.write({'state': 'validated'})

        payslip_t7 = self.create_payslip(
            self.product_emp_A.id,
            fields.Date.to_date('2021-07-1'),
            fields.Date.to_date('2021-07-31'),
            self.contract_open_emp_A.id,
        )

        self.assertRecordValues(
            payslip_t7,
            [
                {
                    'calendar_working_hours': 176,
                    'calendar_working_days': 22,
                    'duty_working_hours': 176,
                    'duty_working_days': 22,
                    'worked_hours': 144,
                    'worked_days': 18,
                    'leave_hours': 32,
                    'leave_days': 4,
                    'unpaid_leave_hours': 32,
                    'unpaid_leave_days': 4,
                }
            ]
        )
