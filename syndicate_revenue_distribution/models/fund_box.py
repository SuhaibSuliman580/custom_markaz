from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SyndicateFundBox(models.Model):
    _name = 'syndicate.fund.box'
    _description = 'Syndicate Fund Box'
    _order = 'sequence, code, id'
    _check_company_auto = True

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    income_account_id = fields.Many2one(
        'account.account',
        string='Income Account',
        required=True,
        check_company=True,
        domain="[('deprecated', '=', False)]",
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        check_company=True,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
    )

    note = fields.Text(string='Notes')

    _sql_constraints = [
        ('fund_box_code_company_unique', 'unique(code, company_id)', 'Fund code must be unique per company.')
    ]

    @api.constrains('income_account_id', 'analytic_account_id', 'company_id')
    def _check_company_consistency(self):
        for rec in self:
            if rec.analytic_account_id.company_id and rec.analytic_account_id.company_id != rec.company_id:
                raise ValidationError("الحساب التحليلي يجب أن يكون لنفس شركة الصندوق أو بدون شركة.")
