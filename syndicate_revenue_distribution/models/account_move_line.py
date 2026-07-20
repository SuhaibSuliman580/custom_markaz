from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    is_distribution_source = fields.Boolean(
        string='مصدر التوزيع',
        default=False,
        copy=False
    )

    is_distribution_generated = fields.Boolean(
        string='سطر توزيع منشأ',
        default=False,
        copy=False
    )

    fund_box_id = fields.Many2one(
        'syndicate.fund.box',
        string='الصندوق',
        readonly=True,
        copy=False,
    )

    distribution_percentage = fields.Float(
        string='نسبة التوزيع',
        readonly=True,
        copy=False,
        digits=(16, 4),
    )

    distribution_source_product_id = fields.Many2one(
        'product.product',
        string='منتج مصدر التوزيع',
        readonly=True,
        copy=False,
    )

    distribution_source_line_id = fields.Many2one(
        'account.move.line',
        string='السطر المصدر',
        copy=False,
        ondelete='set null'
    )

    distribution_generated_line_ids = fields.One2many(
        'account.move.line',
        'distribution_source_line_id',
        string='سطور التوزيع المنشأة',
        copy=False
    )

    hide_distribution_button = fields.Boolean(
        compute='_compute_distribution_ui_flags'
    )

    has_distribution_generated_lines = fields.Boolean(
        compute='_compute_distribution_ui_flags'
    )
    hide_in_invoice_lines = fields.Boolean(
        string='إخفاء في سطور الفاتورة',
        default=False,
        copy=False
    )

    hide_in_journal_items = fields.Boolean(
        string='إخفاء في عناصر اليومية',
        default=False,
        copy=False
    )

    @api.depends(
        'product_id',
        'move_id.state',
        'is_distribution_generated',
        'distribution_generated_line_ids',
    )
    def _compute_distribution_ui_flags(self):
        for line in self:
            hide = True
            if (
                line.move_id
                and line.move_id.is_invoice(include_receipts=True)
                and line.move_id.state == 'draft'
                and not line.is_distribution_generated
                and line.product_id
                and line.product_id.product_tmpl_id.enable_revenue_distribution
            ):
                hide = False
            line.hide_distribution_button = hide
            line.has_distribution_generated_lines = bool(line.distribution_generated_line_ids)

    def _get_distribution_lines(self):
        self.ensure_one()
        product_tmpl = self.product_id.product_tmpl_id
        if not product_tmpl.enable_revenue_distribution:
            return self.env['product.revenue.distribution.line']

        company = self.move_id.company_id
        return product_tmpl.distribution_line_ids.filtered(
            lambda l: l.company_id == company
        ).sorted(key=lambda l: (l.sequence, l.id))

    def _check_can_generate_distribution(self):
        self.ensure_one()

        if self.move_id.state != 'draft':
            raise UserError("لا يمكن إنشاء التوزيع إلا في فاتورة مسودة.")

        if not self.move_id.is_invoice(include_receipts=True):
            raise UserError("التوزيع متاح فقط على الفواتير أو الإيصالات.")

        if not self.product_id:
            raise UserError("يجب اختيار منتج أولاً.")

        if self.display_type in ('line_section', 'line_note'):
            raise UserError("لا يمكن توزيع سطر من نوع ملاحظة أو قسم.")

        if self.is_distribution_generated:
            raise UserError("هذا سطر موزع تلقائياً ولا يمكن إعادة توزيعه.")

        product_tmpl = self.product_id.product_tmpl_id
        if not product_tmpl.enable_revenue_distribution:
            raise UserError("هذا المنتج غير مفعّل له توزيع الإيراد.")

        if not product_tmpl.distribution_line_ids:
            raise UserError("لا توجد أسطر توزيع معرفة على المنتج.")

        distribution_lines = self._get_distribution_lines()
        if not distribution_lines:
            raise UserError("لا توجد أسطر توزيع معرفة على المنتج لشركة الفاتورة.")

        total = sum(distribution_lines.mapped('percentage'))
        if abs(total - 100.0) > 0.0001:
            raise UserError("مجموع نسب التوزيع على المنتج لشركة الفاتورة يجب أن يساوي 100%.")

    def action_generate_distribution_lines(self):
        for line in self:
            line._check_can_generate_distribution()

            if line.distribution_generated_line_ids:
                raise UserError("تم إنشاء أسطر التوزيع مسبقاً لهذا السطر.")

            distribution_lines = line._get_distribution_lines()
            currency = line.move_id.currency_id

            if currency.is_zero(line.price_subtotal):
                raise UserError("لا يمكن توزيع سطر قيمته صفر.")

            created_lines_vals = []
            remaining_subtotal = line.price_subtotal

            for index, dist in enumerate(distribution_lines, start=1):
                if index == len(distribution_lines):
                    part_subtotal = remaining_subtotal
                else:
                    part_subtotal = float_round(
                        line.price_subtotal * (dist.percentage / 100.0),
                        precision_rounding=currency.rounding
                    )
                    remaining_subtotal -= part_subtotal

                new_name = "%s - %s" % (
                    line.name or line.product_id.display_name,
                    dist.fund_box_id.name if dist.fund_box_id else dist.account_id.display_name
                )

                vals = {
                    'move_id': line.move_id.id,
                    'product_id': line.product_id.id,
                    'name': new_name,
                    'quantity': 1.0,
                    'price_unit': part_subtotal,
                    'tax_ids': [(6, 0, line.tax_ids.ids)],
                    'partner_id': line.partner_id.id,
                    'account_id': dist.account_id.id,
                    'currency_id': line.currency_id.id,
                    'analytic_distribution': {
                        dist.analytic_account_id.id: 100,
                    } if dist.analytic_account_id else False,
                    'is_distribution_generated': True,
                    'distribution_source_line_id': line.id,
                    'fund_box_id': dist.fund_box_id.id,
                    'distribution_percentage': dist.percentage,
                    'distribution_source_product_id': line.product_id.id,
                }
                created_lines_vals.append(vals)

            # نبقي السطر الأصلي لكن نخفيه من تبويب Journal Items
            line.write({
                'is_distribution_source': True,
                'quantity': 1.0,
                'price_unit': 0.0,
                'tax_ids': [(5, 0, 0)],
            })

            for vals in created_lines_vals:
                self.env['account.move.line'].create(vals)

    def action_clear_distribution_lines(self):
        for line in self:
            if line.move_id.state != 'draft':
                raise UserError("لا يمكن حذف التوزيع إلا في فاتورة مسودة.")

            generated_lines = line.distribution_generated_line_ids.filtered(lambda l: l.is_distribution_generated)
            if generated_lines:
                generated_lines.unlink()

            line.write({
                'is_distribution_source': False,
                'hide_in_invoice_lines': False,
                'hide_in_journal_items': False,
            })
