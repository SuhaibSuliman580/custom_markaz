import pytz
from datetime import datetime, time
from odoo import fields, models, api

from .browsable_object import WorkedDays


class HrPayslipWorkedDays(models.Model):
    _name = 'hr.payslip.worked_days'
    _description = 'Payslip Worked Days'
    _order = 'contract_id, paid_rate desc'
    _rec_name = 'entry_type_id'

    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    entry_type_id = fields.Many2one('hr.work.entry.type', string='Work Entry Type', required=True, ondelete='cascade', index=True)
    code = fields.Char(related='entry_type_id.code', help="The code that can be used in the salary rules")
    contract_id = fields.Many2one('hr.contract', string='Contract')
    date_from = fields.Date(string='Date From', help="Start date of the salary cycle, "
                            "used to calculate the Calendar Working Days/Hours in the cycle")
    date_to = fields.Date(string='Date To', help="End date of the salary cycle, "
                          "used to calculate the Calendar Working Days/Hours in the cycle")
    calendar_working_hours = fields.Float(
        string='Calendar Working Hours',
        compute='_compute_calendar_working_days_hours', store=True,
        help="Total Working Hours (excl. global leaves) for the FULL months crossing the paylip according"
        " to the corresponding working schedule.")
    calendar_working_days = fields.Float(
        string='Calendar Working Days',
        compute='_compute_calendar_working_days_hours', store=True,
        help="Total Working Days (excl. global leaves) for the FULL months crossing the paylip according"
        " to the corresponding working schedule.")
    number_of_days = fields.Float(string='Number of Days')
    number_of_hours = fields.Float(string='Number of Hours')
    work_entry_ids = fields.Many2many('hr.work.entry', string='Work Entries')
    paid_rate = fields.Float(string='Paid Rate',
                             compute='_compute_paid_rate', store=True,
                             help="Paid rate of this work, computed by the following formula:\n"
                             "* If contract is on day rate basis: Number of Days of Worked days / Calendar Working Days;\n"
                             "* If contract is on hour rate basis: Number of Hours of Worked days / Calendar Working Hours")

    @api.depends('date_from', 'date_to', 'contract_id')
    def _compute_calendar_working_days_hours(self):
        for r in self:
            if not r.contract_id or not r.date_from or not r.date_to:
                continue
            calendar = r.contract_id.resource_calendar_id
            tz = pytz.timezone(calendar.tz)
            date_from = datetime.combine(r.date_from, time.min)
            date_to = datetime.combine(r.date_to, time.max)
            # set timezone
            date_from = date_from.astimezone(tz)
            date_to = date_to.astimezone(tz)
            data = calendar.get_total_work_duration_data(date_from, date_to)
            r.calendar_working_hours = data['hours']
            r.calendar_working_days = data['days']

    @api.depends('number_of_hours', 'number_of_days',
                 'calendar_working_hours', 'calendar_working_days')
    def _compute_paid_rate(self):
        paid_works = self._filter_worked_day_compute_salary()
        for r in self:
            paid_rate = 0.0
            if r in paid_works and r.calendar_working_hours and r.calendar_working_days:
                if r.contract_id.salary_computation_mode == 'hour_basis':
                    paid_rate = r.number_of_hours / r.calendar_working_hours
                else:
                    paid_rate = r.number_of_days / r.calendar_working_days
            r.paid_rate = paid_rate

    def _filter_worked_day_compute_salary(self):
        return self.filtered(lambda r: not r.entry_type_id.is_unpaid)

    def get_workedday_obj(self):
        """
        Get a WorkedDays object for usage in salary rule python code
        @return: WorkedDays object
        @rtype: WorkedDays
        """
        worked_days_dict = {}
        for code in self.mapped('code'):
            worked_days_dict[code] = self.filtered(lambda r: r.code == code)
        return WorkedDays(self.payslip_id.employee_id.id, worked_days_dict, self.env)
