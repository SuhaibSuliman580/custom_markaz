from odoo import models, fields, api, _
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
        string='Fund Box',
        domain="[('active', '=', True), '|', ('branch_id', '=', False), ('branch_id', '=', product_branch_id)]",
    )

    branch_id = fields.Many2one(
        'res.branch',
        string='Fund Box Branch',
        related='fund_box_id.branch_id',
        store=True,
        readonly=True,
    )

    product_branch_id = fields.Many2one(
        'res.branch',
        string='Product Branch',
        related='product_tmpl_id.branch_id',
        store=True,
        readonly=True,
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

    @api.constrains('fund_box_id', 'product_tmpl_id')
    def _check_branch_consistency(self):
        for rec in self:
            if rec.fund_box_id and rec.product_tmpl_id.branch_id and rec.fund_box_id.branch_id and rec.fund_box_id.branch_id != rec.product_tmpl_id.branch_id:
                raise ValidationError(_(
                    "The fund box branch (%(fund_branch)s) must match the product branch (%(product_branch)s).",
                    fund_branch=rec.fund_box_id.branch_id.display_name,
                    product_branch=rec.product_tmpl_id.branch_id.display_name,
                ))
