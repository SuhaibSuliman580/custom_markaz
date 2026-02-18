from odoo import fields, models, api, _
from odoo.tools import float_compare, formatLang

from .hr_contract import TAX_POLICY


class PersonalTaxRule(models.Model):
    _name = 'personal.tax.rule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence ASC, country_id, id'
    _rec_name = 'country_id'
    _description = 'Personal Tax Rule'

    sequence = fields.Integer(string='Sequence', default=10, required=True, tracking=True, index=True)
    country_id = fields.Many2one('res.country', required=True, tracking=True, default=lambda self: self.env.company.country_id)
    currency_id = fields.Many2one(related='country_id.currency_id', store=True, tracking=True)
    personal_tax_policy = fields.Selection(TAX_POLICY,
                                           string='Tax Policy', required=True, default='escalation', tracking=True,
                                           help="The taxation policy applied to the net income of the employee during payslips computation.\n"
                                           "- Progressive Tax Table: the tax rate varies according to the escalation rules defined below;\n"
                                           "- Flat Rate: No matter how much the income is, a flat rate defined below will always"
                                           " be applied.")
    personal_tax_flat_rate = fields.Float(string='Flat Rate', default=0.0, tracking=True,
                                          help="The flat rate in percentage applied to the personal net income.\n"
                                          "Note: This has no affect if the Personal Tax Policy is not Flat Rate")
    progress_ids = fields.One2many('personal.tax.rule.escalation', 'rule_id', string='Progressive Tax Table')
    apply_tax_base_deduction = fields.Boolean(string='Apply Tax Base Deduction', tracking=True,
                                              compute='_compute_apply_tax_base_deduction', store=True, readonly=False,
                                              help="If enabled, deduction will be applied during tax base calculation.")
    personal_tax_base_ded = fields.Monetary('Personal Tax Base Deduction', default=0.0, required=True, tracking=True,
                                     help='The base for personal tax calculation')
    dependent_tax_base_ded = fields.Monetary('Base Deduction on each Dependent', default=0.0, required=True, tracking=True,
                                             help="The amount on each dependent basis added to the Personal Tax Base Deduction.")

    def _prepare_payslip_personal_income_tax_data(self, payslip):
        self.ensure_one()
        income = payslip.personal_tax_base
        if income <= 0:
            return []
        vals_list = []
        if self.personal_tax_policy == 'flat_rate':
            vals_list.append({
                'personal_tax_rule_id': self.id,
                'upper_base': income,
                'personal_tax_policy': 'flat_rate',
                'personal_tax_rule_escalation_id': False,
                'base': income,
                'rate': self.personal_tax_flat_rate,
                'currency_id': payslip.currency_id.id
                })
        elif self.personal_tax_policy == 'escalation':
            for rule in self.progress_ids.sorted('rate', reverse=True):
                rule_base = rule._get_base(payslip)
                if float_compare(income, rule_base, precision_rounding=payslip.currency_id.rounding or 0.01) == 1:
                    base = income - rule.base
                    vals_list.append({
                        'personal_tax_rule_id': self.id,
                        'upper_base': income,
                        'personal_tax_policy': 'escalation',
                        'personal_tax_rule_escalation_id': rule.id,
                        'base': base,
                        'rate': rule.rate,
                        'currency_id': payslip.currency_id.id
                        })
                    income -= base
        return vals_list

    @api.depends('country_id', 'personal_tax_policy')
    def _compute_apply_tax_base_deduction(self):
        for r in self:
            r.apply_tax_base_deduction = r._set_apply_tax_base_deduction()

    @api.depends('personal_tax_policy', 'country_id', 'apply_tax_base_deduction')
    def _compute_display_name(self):
        for r in self:
            r.display_name = r._get_rule_display_name()

    def _get_rule_display_name(self):
        if self.personal_tax_policy == 'escalation':
            name = _('Progressive Tax Table for %s') % self.country_id.name
        elif self.personal_tax_policy == 'flat_rate':
            rate = formatLang(self.env, self.personal_tax_flat_rate, digits=2)
            name = _('Personal Tax Flat Rate %s%s for %s') % (rate, '%', self.country_id.name)
        else:
            name = self.country_id.name
        if not self.apply_tax_base_deduction:
            name += _(" [Without Tax Base Deduction]")
        return name

    def _set_apply_tax_base_deduction(self):
        """
        Hooking method to set value for the field apply_tax_base_deduction.
        It always returns True but other modules (e.g. locallized ones) can override to provide another when needed.
        """
        self.ensure_one()
        return True
