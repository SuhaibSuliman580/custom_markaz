from odoo import models, fields, api
from odoo.exceptions import ValidationError


class SyndicateRevenueDistributionTemplate(models.Model):
    _name = 'syndicate.revenue.distribution.template'
    _description = 'Revenue Distribution Template'
    _order = 'company_id, code, name, id'
    _check_company_auto = True

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

    line_ids = fields.One2many(
        'syndicate.revenue.distribution.template.line',
        'template_id',
        string='Template Lines',
    )

    total_percentage = fields.Float(
        string='Total Percentage',
        compute='_compute_total_percentage',
        digits=(16, 4),
    )

    note = fields.Text(string='Notes')

    _sql_constraints = [
        (
            'template_code_company_unique',
            'unique(code, company_id)',
            'Template code must be unique per company.',
        ),
    ]

    @api.depends('line_ids.percentage')
    def _compute_total_percentage(self):
        for rec in self:
            rec.total_percentage = sum(rec.line_ids.mapped('percentage'))


class SyndicateRevenueDistributionTemplateLine(models.Model):
    _name = 'syndicate.revenue.distribution.template.line'
    _description = 'Revenue Distribution Template Line'
    _order = 'template_id, sequence, id'
    _check_company_auto = True

    template_id = fields.Many2one(
        'syndicate.revenue.distribution.template',
        string='Template',
        required=True,
        ondelete='cascade',
        check_company=True,
    )

    sequence = fields.Integer(default=10)

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        related='template_id.company_id',
        store=True,
        readonly=True,
    )

    fund_box_id = fields.Many2one(
        'syndicate.fund.box',
        string='Fund Box',
        required=True,
        check_company=True,
        domain="[('active', '=', True), ('company_id', '=', company_id)]",
    )

    account_id = fields.Many2one(
        'account.account',
        string='Income Account',
        related='fund_box_id.income_account_id',
        store=True,
        readonly=True,
    )

    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        related='fund_box_id.analytic_account_id',
        store=True,
        readonly=True,
    )

    percentage = fields.Float(
        string='Percentage',
        required=True,
        digits=(16, 4),
        default=100.0,
    )

    _sql_constraints = [
        (
            'template_fund_box_unique',
            'unique(template_id, fund_box_id)',
            'Fund Box must be unique per template.',
        ),
    ]

    @api.onchange('company_id')
    def _onchange_company_id(self):
        for rec in self:
            if rec.fund_box_id and rec.fund_box_id.company_id != rec.company_id:
                rec.fund_box_id = False

    @api.constrains('percentage')
    def _check_percentage(self):
        for rec in self:
            if rec.percentage <= 0:
                raise ValidationError("النسبة يجب أن تكون أكبر من صفر.")
            if rec.percentage > 100:
                raise ValidationError("النسبة لا يمكن أن تتجاوز 100%.")

    @api.constrains('company_id', 'fund_box_id')
    def _check_fund_box_consistency(self):
        for rec in self:
            if rec.fund_box_id and not rec.fund_box_id.active:
                raise ValidationError("لا يمكن استخدام صندوق غير فعال في قالب توزيع الإيرادات.")
            if rec.fund_box_id and rec.company_id and rec.fund_box_id.company_id != rec.company_id:
                raise ValidationError("لا يمكن استخدام صندوق تابع لشركة مختلفة عن شركة قالب التوزيع.")
