from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _auto_generate_distribution_lines(self):
        for move in self:
            if move.state != 'draft':
                continue

            if not move.is_invoice(include_receipts=True):
                continue

            candidate_lines = move.invoice_line_ids.filtered(
                lambda l:
                    l.product_id
                    and l.display_type == 'product'
                    and not l.is_distribution_generated
                    and not l.distribution_generated_line_ids
                    and l.product_id.product_tmpl_id.enable_revenue_distribution
            )

            for line in candidate_lines:
                line.action_generate_distribution_lines()

            # بعد إنشاء سطور التوزيع، احذف السطور الأصلية الصفرية فقط
            source_lines = move.invoice_line_ids.filtered(
                lambda l:
                    l.is_distribution_source
                    and not l.is_distribution_generated
                    and l.price_unit == 0.0
            )
            if source_lines:
                source_lines.unlink()

    def action_post(self):
        self._auto_generate_distribution_lines()
        return super().action_post()