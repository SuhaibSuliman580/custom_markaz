from odoo import fields, models, api, _
from odoo.tools import format_amount


class PersonalTaxRuleEscalation(models.Model):
    _name = 'personal.tax.rule.escalation'
    _inherit = 'mail.thread'
    _order = 'rate ASC, rule_id'
    _description = 'Personal Tax Rule Escalation'

    rule_id = fields.Many2one('personal.tax.rule', string='Personal Tax Rule', ondelete='cascade', required=True, index=True)
    country_id = fields.Many2one(related='rule_id.country_id', store=True)
    currency_id = fields.Many2one(related='rule_id.currency_id', store=True)
    base = fields.Monetary(string='Tax Base', default=0.0, required=True, tracking=True, index=True)
    rate = fields.Float(string='Tax Rate', default=0.0, required=True, tracking=True,
                        help="The personal tax rate in percentage that will be applied for the amount that is greater than the Tax Base.")

    @api.depends('base', 'currency_id')
    def _compute_display_name(self):
        for r in self:
            if r.currency_id:
                r.display_name = _('Greater than %s') % format_amount(r.env, r.base, r.currency_id)
            else:
                r.display_name = _('Greater than %s') % r.base

    def _get_base(self, payslip):
        date = payslip.date_to or fields.Date.today()
        self.ensure_one()
        if payslip.currency_id != self.currency_id:
            rule_base = self.country_id.currency_id._convert(self.base, payslip.currency_id, payslip.company_id, date)
        else:
            rule_base = self.base
        return rule_base
