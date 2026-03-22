from odoo import models, fields


class SyndicateFundBox(models.Model):
    _name = 'syndicate.fund.box'
    _description = 'Syndicate Fund Box'
    _order = 'sequence, code, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True)

    income_account_id = fields.Many2one(
        'account.account',
        string='Income Account',
        required=True,
        domain="[('deprecated', '=', False)]",
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )

    note = fields.Text(string='Notes')

    _sql_constraints = [
        ('fund_box_code_unique', 'unique(code)', 'Fund code must be unique.')
    ]
