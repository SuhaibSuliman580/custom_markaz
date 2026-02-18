from odoo import fields, models, api
from .hr_contract import TAX_POLICY


class ContractType(models.Model):
    _name = 'hr.contract.type'
    _inherit = ['hr.contract.type', 'mail.thread', 'mail.activity.mixin']

    # Override `name` field
    name = fields.Char(tracking=True)

    salary_computation_mode = fields.Selection([
        ('hour_basis', 'Hour Basis'),
        ('day_basis', 'Day Basis')
        ], string='Salary Computation Mode', default='hour_basis', required=True, tracking=True,
        help="How the employee salary would be computed in salary rules, based on either working days or working hours:\n"
        "* Hour Basis: salary would be computed based on working hours;\n"
        "* Day Basis: salary would be computed based on working days;\n")
    personal_tax_policy = fields.Selection(TAX_POLICY, default='escalation',
       string='Personal Tax Policy', required=True, tracking=True,
       help="The taxation policy applied to the net income of the payslips of this contract.\n"
       "- Progressive Tax Table: the tax rate varies according to the country's escalation taxation policy"
       " which is defined in Configuration > Personal Tax Rules;\n"
       "- Flat Rate: No matter how much the income is, a flat rate defined in Configuration"
       " > Personal Tax Rules will always  be applied.")
    country_id = fields.Many2one('res.country', string='Country', required=True, tracking=True, default=lambda self: self.env.company.country_id)
    personal_tax_rule_id = fields.Many2one('personal.tax.rule',
        string='Tax Rule', tracking=True,
        domain="[('personal_tax_policy', '=', personal_tax_policy)]",
        compute="_compute_tax_rule", store=True, readonly=False,
        help="The personal income tax rule applied to payslips of this contract")

    @api.depends('personal_tax_policy', 'country_id')
    def _compute_tax_rule(self):
        tax_rules = self.env['personal.tax.rule'].search([
            ('country_id', 'in', self.country_id.ids),
            ('personal_tax_policy', 'in', self.mapped('personal_tax_policy'))
            ])
        for r in self:
            r.personal_tax_rule_id = tax_rules.filtered(
                lambda rule:
                rule.country_id == r.country_id
                and rule.personal_tax_policy == r.personal_tax_policy
                )[:1]
