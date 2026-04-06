from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SyndicateFundBox(models.Model):
    _name = 'syndicate.fund.box'
    _description = 'Syndicate Fund Box'
    _order = 'sequence, code, id'

    sequence = fields.Integer(default=10)
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    active = fields.Boolean(default=True)
    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        default=lambda self: self.env.user.branch_id.id if self.env.user.branch_id else False,
        index=True,
    )

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

    @api.onchange('branch_id')
    def _onchange_branch_id(self):
        for rec in self:
            if rec.branch_id and self.env.user.branch_id and rec.branch_id != self.env.user.branch_id:
                raise UserError(_(
                    "Please select the active branch only. Switch branch from the header first, then create or edit the fund box."
                ))

    @api.model
    def create(self, vals):
        if not vals.get('branch_id') and self.env.user.branch_id:
            vals['branch_id'] = self.env.user.branch_id.id
        return super().create(vals)
