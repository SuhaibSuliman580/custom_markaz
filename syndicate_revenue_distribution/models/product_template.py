from odoo import models, fields, api
from odoo.exceptions import ValidationError


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
