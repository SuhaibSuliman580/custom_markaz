# -*- coding: utf-8 -*-
from datetime import timedelta, datetime

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
import logging
_logger = logging.getLogger(__name__)

class Employee(models.Model):
    _name = "hr.employee"
    _inherit = "hr.employee"

    # att_user_id = fields.Char("Attendance User ID")

    @api.constrains('att_user_id')
    def _check_att_user_id(self):
        for employee in self:
            if employee.att_user_id:
                att_employee_ids = self.search(
                    [('att_user_id', '=', employee.att_user_id)])
                if len(att_employee_ids) > 1:
                    raise ValidationError('Attendance User ID Must be uniq')

    def convert_log_to_attendance(self):
        self.ensure_one()
        attendance_obj = self.env['hr.attendance']
        log_obj = self.env['biometric.log']
        log_domain = [('employee_id', '=', self.id)]
        _logger.info(
            'BIO-ATTENDANCE==> Convert Biometric Log to attendnace for employee : %s' % self.name)
        prev_attendance_id = attendance_obj.search(
            [('employee_id', '=', self.id)],
            order='check_in desc', limit=1)
        if prev_attendance_id:

            if prev_attendance_id.check_out:
                log_domain += [('name', '>', prev_attendance_id.check_out)]
            else:
                log_domain += [('name', '>', prev_attendance_id.check_in)]

        log_ids = log_obj.search(log_domain, order='name asc')
        for log in log_ids:
            log_time = log.name
            prev_attendance_id = attendance_obj.search(
                [('employee_id', '=', self.id)],
                order='check_in desc', limit=1)
            min_time = log.machine.min_time
            max_time = log.machine.max_time

            if prev_attendance_id and not prev_attendance_id.check_out and log.type == 'in':
                prev_att_checkin_time = prev_attendance_id.check_in

                if min_time >= (log_time - prev_att_checkin_time):
                    continue
                else:
                    prev_attendance_id.write({
                        'check_out': prev_attendance_id.check_in,
                        'state': 'fixout'
                    })
                    new_attendance = attendance_obj.create({
                        'employee_id': self.id,
                        'check_in': log_time,
                    })
                    continue
            elif prev_attendance_id and not prev_attendance_id.check_out and log.type == 'out':
                prev_att_checkin_time = prev_attendance_id.check_in
                if max_time >= (log_time - prev_att_checkin_time):
                    prev_attendance_id.write({
                        'check_out': log_time,
                    })

                else:

                    prev_attendance_id.write({
                        'check_out': prev_att_checkin_time + timedelta(
                            milliseconds=1),
                        'state': 'fixout'
                    })

                    new_attendance = attendance_obj.create({
                        'employee_id': self.id,
                        'check_in': log_time - timedelta(milliseconds=1),
                        'check_out': log_time,
                        'state': 'fixin'

                    })

            elif prev_attendance_id and prev_attendance_id.check_out and log.type == 'in':
                prev_att_checkout_time = prev_attendance_id.check_out
                new_attendance = attendance_obj.create({
                    'employee_id': self.id,
                    'check_in': log_time,
                    'state': 'right'

                })
            elif prev_attendance_id and prev_attendance_id.check_out and log.type == 'out':
                prev_att_checkout_time = prev_attendance_id.check_out
                if min_time >= (log_time - prev_att_checkout_time):
                    prev_attendance_id.write({'check_out': log_time})

                else:
                    new_attendance = attendance_obj.create({
                        'employee_id': self.id,
                        'check_in': log_time - timedelta(milliseconds=1),
                        'check_out': log_time,
                        'state': 'fixin'

                    })

            elif not prev_attendance_id:
                new_attendance = attendance_obj.create({
                    'employee_id': self.id,
                    'check_in': log_time,
                    'state': 'right'

                })


class EmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    att_user_id = fields.Char("Attendance User ID")
    religion = fields.Selection(
        [('mus', 'Muslem'), ('chris', 'Christian'), ('other', 'Others')],
        string="Religion")
    military_status = fields.Selection(
        [('not_req', 'Not Required'), ('post', 'Postponed'),
         ('complete', 'complete'), ('exemption', 'Exemption'),
         ('current', 'Currently serving ')], string="Military Status")
    # age = fields.Integer(string="Age", compute="_calculate_age", readonly=True)
    start_date = fields.Date(string="Start Working At")
    edu_major = fields.Char(string="major")
    edu_grad = fields.Selection(
        [('ex', 'Excellent'), ('vgod', 'Very Good'), ('god', 'Good'),
         ('pas', 'Pass')],
        string="Grad")
    edu_note = fields.Text("Education Notes")
    experience_y = fields.Integer(compute="_calculate_experience",
                                  string="Experience",
                                  help="experience in our company", store=True)
    experience_m = fields.Integer(compute="_calculate_experience",
                                  string="Experience monthes", store=True)
    experience_d = fields.Integer(compute="_calculate_experience",
                                  string="Experience dayes", store=True)

    @api.depends("start_date")
    def _calculate_experience(self):
        for emp in self.search([]):
            if emp.start_date:
                date_format = '%Y-%m-%d'
                current_date = (datetime.today()).strftime(date_format)
                d1 = emp.start_date
                d2 = datetime.strptime(current_date, date_format).date()
                r = relativedelta(d2, d1)
                emp.experience_y = r.years
                emp.experience_m = r.months
                emp.experience_d = r.days
            else:
                emp.experience_y = 0
                emp.experience_m = 0
                emp.experience_d = 0
