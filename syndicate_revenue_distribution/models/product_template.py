from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    enable_revenue_distribution = fields.Boolean(
        string='Enable Revenue Distribution'
    )

    distribution_line_ids = fields.One2many(
        'product.revenue.distribution.line',
        'product_tmpl_id',
        string='Revenue Distribution Lines'
    )

    revenue_distribution_template_id = fields.Many2one(
        'syndicate.revenue.distribution.template',
        string='Revenue Distribution Template',
        domain="[('active', '=', True)]",
    )

    distribution_total = fields.Float(
        string='Distribution Total',
        compute='_compute_distribution_total'
    )

    @api.depends('distribution_line_ids.percentage', 'distribution_line_ids.company_id')
    @api.depends_context('company')
    def _compute_distribution_total(self):
        for rec in self:
            company = self.env.company
            company_lines = rec.distribution_line_ids.filtered(lambda l: l.company_id == company)
            rec.distribution_total = sum(company_lines.mapped('percentage'))

    @api.constrains('enable_revenue_distribution', 'distribution_line_ids', 'distribution_line_ids.percentage', 'distribution_line_ids.company_id')
    def _check_distribution_setup(self):
        for rec in self:
            if not rec.enable_revenue_distribution:
                continue
            if not rec.distribution_line_ids:
                raise ValidationError("يجب إدخال أسطر توزيع الإيراد للمنتج.")

            for company in rec.distribution_line_ids.mapped('company_id'):
                lines = rec.distribution_line_ids.filtered(lambda l: l.company_id == company)
                total = sum(lines.mapped('percentage'))
                if abs(total - 100.0) > 0.0001:
                    raise ValidationError(
                        "مجموع نسب التوزيع للمنتج في الشركة %s يجب أن يساوي 100%%."
                        % company.display_name
                    )

    def action_apply_revenue_distribution_template(self):
        for rec in self:
            template = rec.revenue_distribution_template_id
            if not template:
                raise UserError("يجب اختيار قالب توزيع الإيرادات أولاً.")
            if not template.active:
                raise UserError("لا يمكن تطبيق قالب غير فعال.")
            if abs(template.total_percentage - 100.0) > 0.0001:
                raise UserError("يجب أن يكون مجموع نسب القالب 100%.")
            if rec.distribution_line_ids:
                raise UserError("يوجد توزيع حالي، يرجى حذف السطور قبل تطبيق القالب.")

            rec.distribution_line_ids = [
                (0, 0, {
                    'sequence': line.sequence,
                    'company_id': line.company_id.id,
                    'fund_box_id': line.fund_box_id.id,
                    'percentage': line.percentage,
                })
                for line in template.line_ids.sorted(key=lambda l: (l.sequence, l.id))
            ]
            rec.enable_revenue_distribution = True
