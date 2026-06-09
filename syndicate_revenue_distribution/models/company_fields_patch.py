# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import ValidationError


class SyndicateFundBoxCompanyPatch(models.Model):
    _inherit = 'syndicate.fund.box'

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

    _sql_constraints = [
        ('fund_box_code_company_unique', 'unique(code, company_id)', 'Fund code must be unique per company.')
    ]

    @api.constrains('income_account_id', 'analytic_account_id', 'company_id')
    def _check_company_consistency_patch(self):
        for rec in self:
            if rec.analytic_account_id.company_id and rec.analytic_account_id.company_id != rec.company_id:
                raise ValidationError('الحساب التحليلي يجب أن يكون لنفس شركة الصندوق أو بدون شركة.')


class ProductRevenueDistributionLineCompanyPatch(models.Model):
    _inherit = 'product.revenue.distribution.line'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='fund_box_id.company_id',
        store=True,
        readonly=True,
    )
