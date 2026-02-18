from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class HrPayrollContribActionChangeBase(models.TransientModel):
    _name = 'hr.payroll.contrib.action.change.base'
    _inherit = 'abstract.hr.payroll.contrib.act'
    _description = "Payroll Contribution Action Change Base"

    payroll_contribution_reg_ids = fields.Many2many('hr.payroll.contribution.register', relation='wizard_action_change_base_payroll_contrib_rel',
                                                    string='Payroll Contribution Register', required=True)
    currency_id = fields.Many2one(related='payroll_contribution_reg_ids.currency_id')
    contribution_base = fields.Monetary('Computation Base', required=True,
                                     help="The base for calculation of payroll contribution")

    @api.constrains('payroll_contribution_reg_ids')
    def _check_payroll_contribution_reg_ids(self):
        for r in self:
            if len(r.mapped('payroll_contribution_reg_ids.currency_id')) > 1:
                raise ValidationError(_("All the selected Payroll Contribution Registers must have the same currency"))

    @api.onchange('payroll_contribution_reg_ids')
    def _onchange_payroll_contribution_reg_ids(self):
        if self.payroll_contribution_reg_ids:
            self.contribution_base = self.payroll_contribution_reg_ids[0].contribution_base

    def process(self):
        self.ensure_one()
        self.payroll_contribution_reg_ids.with_context(
            call_wizard=False,
            contribution_base=self.contribution_base,
            contribution_base_change_date=self.date
            ).action_change_base()
