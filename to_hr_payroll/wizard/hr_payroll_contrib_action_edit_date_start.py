from odoo import models, fields, _
from odoo.exceptions import UserError
from odoo.tools.misc import format_date


class HrPayrollContribActionEditDate(models.TransientModel):
    _name = 'hr.payroll.contrib.action.edit.date.start'
    _description = "Edit Date Start of Payroll Contribution History"

    payroll_contribution_history_id = fields.Many2one('hr.payroll.contribution.history',
                                                      required=True, string='Payroll Contribution History')
    date_start = fields.Date(string='New Start Date', default=fields.Date.today, required=True)

    def action_confirm(self):
        self.ensure_one()
        payroll_contribution_reg = self.payroll_contribution_history_id.payroll_contribution_reg_id
        if self.date_start < payroll_contribution_reg.date_from:
            raise UserError(_("The new date must be greater than or equal to the start date of the Payroll Contribution Register `%s` which is '%s'")
                            % (
                                payroll_contribution_reg.display_name,
                                format_date(self.env, payroll_contribution_reg.date_from)
                                )
                            )
        self.payroll_contribution_history_id.write({'date_from': self.date_start})
