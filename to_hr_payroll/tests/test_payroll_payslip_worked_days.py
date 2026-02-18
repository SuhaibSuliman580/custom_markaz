from datetime import datetime, time, timedelta
import pytz

from odoo import fields
from odoo.tests import tagged

from .common import TestPayrollCommon


@tagged('post_install', '-at_install')
class TestPayrollPayslipWorkedDay(TestPayrollCommon):

    @classmethod
    def setUpClass(cls):
        super(TestPayrollPayslipWorkedDay, cls).setUpClass()
        cls.employee_1 = cls.create_employee('New Employee A')
        cls.contract_1 = cls.create_contract(
            cls.employee_1.id,
            fields.Date.to_date('2023-01-01'),
            state='open')
        cls.contract_1.resource_calendar_id.global_leave_ids.unlink()
        cls.contract_1._cron_generate_missing_work_entries()
        cls.calendar_tz = pytz.timezone(cls.contract_1.resource_calendar_id.tz)

        cls.work_entry_type_attendance = cls.env.ref('hr_work_entry.work_entry_type_attendance')
        cls.work_entry_type_global_holiday = cls.env.ref('hr_work_entry_contract.work_entry_type_leave')

    def test_worked_day_01(self):
        """
        Test: Worked Days:
            - number of days/hours of Worked Days = total duration/duration_days of all work entries for the period
        """
        today = fields.Date.today()
        date_from = fields.Date.start_of(today, 'month')
        date_to = fields.Date.end_of(today, 'month')
        date_start = datetime.combine(date_from, time(0, 0))
        date_stop = datetime.combine(date_to, time(22, 0))

        work_entries_in_month = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_1.id),
            ('date_start', '>=', date_start),
            ('date_stop', '<=', date_stop),
        ])
        work_entries_in_month.write({'state': 'validated'})
        payslip = self.create_payslip(self.employee_1.id, date_from, date_to)
        self.assertRecordValues(
            payslip.worked_days_line_ids,
            [{
                'entry_type_id': work_entries_in_month.work_entry_type_id.id,
                'contract_id': self.contract_1.id,
                'number_of_hours': sum(work_entries_in_month.mapped('duration')),
                'number_of_days': sum(work_entries_in_month.mapped('duration_days'))
            }])

    def test_worked_day_02(self):
        """
        Test: Worked Days - has leaves (other work entry type)
            - number of days/hours of Worked Days = total duration/duration_days of all work entries for the period
        """
        today = fields.Date.today()
        date_from = fields.Date.start_of(today, 'month')
        date_to = fields.Date.end_of(today, 'month')
        date_start = datetime.combine(date_from, time(0, 0))
        date_stop = datetime.combine(date_to, time(22, 0))

        # Time Off
        leave_type = self.env['hr.leave.type'].search([('unpaid', '=', True)], limit=1)
        work_entry_type_unpaid = leave_type.work_entry_type_id
        # make sure the holiday falls within this month
        if today.day < 15:
            leave_date_from = fields.Date.end_of(today, 'week') + timedelta(days=1)
        else:
            leave_date_from = fields.Date.start_of(today, 'week')

        leave_date_start = datetime.combine(leave_date_from, time(8, 0))
        leave_date_start = self.calendar_tz.localize(leave_date_start)
        leave_date_start = leave_date_start.astimezone(pytz.utc).replace(tzinfo=None)
        leave_date_end = datetime.combine(leave_date_from, time(17, 0))
        leave_date_end = self.calendar_tz.localize(leave_date_end)
        leave_date_end = leave_date_end.astimezone(pytz.utc).replace(tzinfo=None)

        leave_unpaid = self.create_holiday('Test Leave 1', self.employee_1.id,
                                           leave_type.id,
                                           leave_date_start,
                                           leave_date_end)
        leave_unpaid.action_validate()
        work_entries_in_month = self.env['hr.work.entry'].search([
            ('employee_id', '=', self.employee_1.id),
            ('date_start', '>=', date_start),
            ('date_stop', '<=', date_stop),
        ])
        work_entries_in_month.write({'state': 'validated'})
        work_entries_attendance = work_entries_in_month.filtered(lambda r: r.work_entry_type_id == self.work_entry_type_attendance)
        payslip = self.create_payslip(self.employee_1.id, date_from, date_to)
        self.assertEqual(len(payslip.worked_days_line_ids), 2)
        work_day_attendance = payslip.worked_days_line_ids.filtered(lambda r: r.entry_type_id == self.work_entry_type_attendance)
        self.assertRecordValues(
            work_day_attendance,
            [{
                'contract_id': self.contract_1.id,
                'number_of_hours': sum(work_entries_attendance.mapped('duration')),
                'number_of_days': sum(work_entries_attendance.mapped('duration_days'))
            }])
        work_day_unpaid = payslip.worked_days_line_ids.filtered(lambda r: r.entry_type_id == work_entry_type_unpaid)
        self.assertRecordValues(
            work_day_unpaid,
            [{
                'contract_id': self.contract_1.id,
                'number_of_hours': 8.0,
                'number_of_days': 1.0
            }])

    def test_03_payslip_info_01(self):
        """
        The working time on the payslip does not include the total public holiday
             - `Public holiday` is not marked as `is_working_day`
        """
        date_from = fields.Date.to_date('2023-10-01')
        date_to = fields.Date.to_date('2023-10-31')
        monday = fields.Date.to_date('2023-10-09')

        date_start = datetime.combine(monday, time(8, 0))
        date_start = self.calendar_tz.localize(date_start)
        date_start = date_start.astimezone(pytz.utc).replace(tzinfo=None)

        date_end = datetime.combine(monday, time(17, 0))
        date_end = self.calendar_tz.localize(date_end)
        date_end = date_end.astimezone(pytz.utc).replace(tzinfo=None)

        # field`is_working_day` is not marked
        self.env['resource.calendar.leaves'].create({
            'name': 'Global Holiday 1',
            'date_from': date_start,
            'date_to': date_end,
            'work_entry_type_id': self.work_entry_type_global_holiday.id
        })
        work_entries = self.employee_1.generate_work_entries(date_from, date_to, force=True)
        work_entries.write({'state': 'validated'})

        payslip = self.create_payslip(self.employee_1.id, date_from, date_to)
        self.assertRecordValues(
            payslip,
            [{
                'calendar_working_hours': 168.0,
                'calendar_working_days': 21,
                'duty_working_hours': 168.0,
                'duty_working_days': 21,
                'worked_hours': 168.0,
                'worked_days': 21.0,
                'leave_days': 0.0,
                'leave_hours': 0.0,
                'unpaid_leave_hours': 0.0,
                'unpaid_leave_days': 0.0,
            }]
        )
        self.assertRecordValues(
            payslip.worked_days_line_ids,
            [{
                'entry_type_id': self.work_entry_type_attendance.id,
                'number_of_hours': 168.0,
                'number_of_days': 21.0,
                'paid_rate': 1.0
            },
            {
                'entry_type_id': self.work_entry_type_global_holiday.id,
                'number_of_hours': 8.0,
                'number_of_days': 1.0,
                'paid_rate': 0.0
            }]
        )

    def test_04_payslip_info_02(self):
        """
        The working time on the payslip include the total public holiday
             - `Public holiday` need to be marked as `is_working_day`
        """
        date_from = fields.Date.to_date('2023-10-01')
        date_to = fields.Date.to_date('2023-10-31')
        monday = fields.Date.to_date('2023-10-09')

        date_start = datetime.combine(monday, time(8, 0))
        date_start = self.calendar_tz.localize(date_start)
        date_start = date_start.astimezone(pytz.utc).replace(tzinfo=None)

        date_end = datetime.combine(monday, time(17, 0))
        date_end = self.calendar_tz.localize(date_end)
        date_end = date_end.astimezone(pytz.utc).replace(tzinfo=None)

        # field `is_working_day` is marked
        WE_Type = self.env['hr.work.entry.type'].create({
            'name': 'Public Holiday - Paid',
            'code': 'PUBLIC_HOLIDAY_PAID',
            'is_leave': True,
        })
        self.env['resource.calendar.leaves'].create({
            'name': 'Global Holiday 1',
            'date_from': date_start,
            'date_to': date_end,
            'is_working_day': True,
            'work_entry_type_id': WE_Type.id
        })
        work_entries = self.employee_1.generate_work_entries(date_from, date_to, force=True)
        work_entries.write({'state': 'validated'})

        payslip = self.create_payslip(self.employee_1.id, date_from, date_to)
        self.assertRecordValues(
            payslip,
            [{
                'calendar_working_hours': 176.0,
                'calendar_working_days': 22,
                'duty_working_hours': 176.0,
                'duty_working_days': 22,
                'worked_hours': 168.0,
                'worked_days': 21.0,
                'leave_days': 1.0,
                'leave_hours': 8.0,
                'unpaid_leave_hours': 0.0,
                'unpaid_leave_days': 0.0,
            }]
        )
        self.assertRecordValues(
            payslip.worked_days_line_ids,
            [{
                'entry_type_id': self.work_entry_type_attendance.id,
                'number_of_hours': 168.0,
                'number_of_days': 21.0,
                'paid_rate': 168.0 / 176.0
            },
            {
                'entry_type_id': WE_Type.id,
                'number_of_hours': 8.0,
                'number_of_days': 1.0,
                'paid_rate': 8.0 / 176.0
            }]
        )
