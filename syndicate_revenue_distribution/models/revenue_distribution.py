from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductRevenueDistributionLine(models.Model):
    _name = 'product.revenue.distribution.line'
    _description = 'Product Revenue Distribution Line'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        required=True,
        ondelete='cascade'
    )

    fund_box_id = fields.Many2one(
        'syndicate.fund.box',
        string='Fund Box'
    )

    account_id = fields.Many2one(
        'account.account',
        string='Income Account',
        required=True,
        domain="[('deprecated', '=', False)]",
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account'
    )

    percentage = fields.Float(
        string='Percentage',
        required=True,
        digits=(16, 4),
        default=100.0
    )

    @api.onchange('fund_box_id')
    def _onchange_fund_box_id(self):
        for rec in self:
            if rec.fund_box_id:
                rec.account_id = rec.fund_box_id.income_account_id
                rec.analytic_account_id = rec.fund_box_id.analytic_account_id

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if rec.percentage <= 0:
                raise ValidationError("النسبة يجب أن تكون أكبر من صفر.")
            if rec.percentage > 100:
                raise ValidationError("النسبة لا يمكن أن تتجاوز 100%.")
