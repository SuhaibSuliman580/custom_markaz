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
        compute='_compute_distribution_total',
        store=True
    )

    @api.depends('distribution_line_ids.percentage')
    def _compute_distribution_total(self):
        for rec in self:
            rec.distribution_total = sum(rec.distribution_line_ids.mapped('percentage'))

    @api.constrains('enable_revenue_distribution', 'distribution_line_ids', 'distribution_total')
    def _check_distribution_setup(self):
        for rec in self:
            if rec.enable_revenue_distribution:
                if not rec.distribution_line_ids:
                    raise ValidationError("يجب إدخال أسطر توزيع الإيراد للمنتج.")
                if abs(rec.distribution_total - 100.0) > 0.0001:
                    raise ValidationError("مجموع نسب التوزيع يجب أن يساوي 100%.")
