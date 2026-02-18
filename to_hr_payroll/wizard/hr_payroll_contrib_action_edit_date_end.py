from odoo import models, fields


class HrPayrollContribActionEditDate(models.TransientModel):
    _name = 'hr.payroll.contrib.action.edit.date.end'
    _description = "Edit Date End of Payroll Contribution History"

    payroll_contribution_history_id = fields.Many2one('hr.payroll.contribution.history',
                                                      required=True, string='Payroll Contribution History')
    date_end = fields.Date(string='New End Date', default=fields.Date.today, required=True)

    def action_confirm(self):
        self.ensure_one()
        self.payroll_contribution_history_id.write({'date_to': self.date_end})
