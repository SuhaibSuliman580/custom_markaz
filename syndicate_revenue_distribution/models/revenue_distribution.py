from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ProductRevenueDistributionLine(models.Model):
    _name = 'product.revenue.distribution.line'
    _description = 'Product Revenue Distribution Line'
    _order = 'company_id, sequence, id'
    _check_company_auto = True

    sequence = fields.Integer(default=10)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    product_tmpl_id = fields.Many2one(
        'product.template',
        string='Product Template',
        required=True,
        ondelete='cascade',
        check_company=True,
    )

    fund_box_id = fields.Many2one(
        'syndicate.fund.box',
        string='Fund Box',
        check_company=True,
        domain="[('company_id', '=', company_id)]",
    )

    account_id = fields.Many2one(
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

    percentage = fields.Float(
        string='Percentage',
        required=True,
        digits=(16, 4),
        default=100.0
    )

    @api.onchange('company_id')
    def _onchange_company_id(self):
        for rec in self:
            if rec.fund_box_id and rec.fund_box_id.company_id != rec.company_id:
                rec.fund_box_id = False
            if rec.analytic_account_id.company_id and rec.analytic_account_id.company_id != rec.company_id:
                rec.analytic_account_id = False

    @api.onchange('fund_box_id')
    def _onchange_fund_box_id(self):
        for rec in self:
            if rec.fund_box_id:
                rec.company_id = rec.fund_box_id.company_id
                rec.account_id = rec.fund_box_id.income_account_id
                rec.analytic_account_id = rec.fund_box_id.analytic_account_id

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if rec.percentage <= 0:
                raise ValidationError("النسبة يجب أن تكون أكبر من صفر.")
            if rec.percentage > 100:
                raise ValidationError("النسبة لا يمكن أن تتجاوز 100%.")

    @api.constrains('company_id', 'fund_box_id', 'analytic_account_id')
    def _check_company_consistency(self):
        for rec in self:
            if rec.fund_box_id and rec.fund_box_id.company_id != rec.company_id:
                raise ValidationError("صندوق الإيراد يجب أن يكون لنفس شركة سطر التوزيع.")
            if rec.analytic_account_id.company_id and rec.analytic_account_id.company_id != rec.company_id:
                raise ValidationError("الحساب التحليلي يجب أن يكون لنفس شركة سطر التوزيع أو بدون شركة.")
