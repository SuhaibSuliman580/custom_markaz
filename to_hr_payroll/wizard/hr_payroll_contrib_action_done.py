from odoo import api, fields, models


class HrPayrollContribActionDone(models.TransientModel):
    _name = 'hr.payroll.contrib.action.done'
    _inherit = 'abstract.hr.payroll.contrib.act'
    _description = "Payroll Contribution Action Done"

    payroll_contribution_reg_ids = fields.Many2many('hr.payroll.contribution.register', relation='wizard_action_done_payroll_contrib_rel', string='Payroll Contribution Register', required=True)

    @api.constrains('payroll_contribution_reg_ids', 'date')
    def _check_date(self):
        super()._check_date()

    def process(self):
        self.ensure_one()
        self.payroll_contribution_reg_ids.write({'date_to': self.date})
        self.payroll_contribution_reg_ids.with_context(date_to=self.date, call_wizard=False).action_done()
