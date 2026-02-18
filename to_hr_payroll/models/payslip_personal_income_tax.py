from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

from .hr_contract import TAX_POLICY


class PayslipPersonnalIncomeTax(models.Model):
    _name = 'payslip.personal.income.tax'
    _rec_name = 'personal_tax_rule_escalation_id'
    _description = 'Payslip Personnal Income Tax'

    slip_id = fields.Many2one('hr.payslip', string='Payslip', required=True, ondelete='cascade', index=True, readonly=True)
    personal_tax_rule_id = fields.Many2one('personal.tax.rule', string='Personal Tax Rule', required=True, readonly=True)
    personal_tax_policy = fields.Selection(TAX_POLICY, string='Tax Policy', readonly=True, required=True)
    personal_tax_rule_escalation_id = fields.Many2one('personal.tax.rule.escalation', string='Tax Escalation', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, readonly=True)
    base = fields.Monetary(string='Tax Computation Base', required=True, readonly=True)
    upper_base = fields.Monetary(string='Taxed Income', required=True, readonly=True)
    rate = fields.Float(string='Tax Rate', required=True, readonly=True)
    tax_amount = fields.Monetary(string='Tax Amount', compute='_compute_tax_amount', store=True)

    @api.constrains('slip_id', 'currency_id')
    def _check_currency(self):
        for r in self:
            if r.currency_id and r.slip_id and r.currency_id != r.slip_id.currency_id:
                raise ValidationError(_("Currency Discrepancy on payslip personal income tax."
                                        " It should be in the same currency as the payslip's."))

    @api.depends('base', 'rate')
    def _compute_tax_amount(self):
        for r in self:
            r.tax_amount = r.base * r.rate / 100.0
