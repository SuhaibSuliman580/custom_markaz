from odoo import models
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def action_open_revenue_distribution_analysis(self):
        self.ensure_one()

        if self.move_type not in ('out_invoice', 'out_refund'):
            raise UserError("تحليل توزيع الإيرادات متاح فقط لفواتير العملاء وإشعاراتهم الدائنة.")

        detail_commands = []
        summary_data = {}

        candidate_lines = self.invoice_line_ids.filtered(
            lambda line:
                line.product_id
                and line.display_type in (False, 'product')
                and not line.is_distribution_generated
                and line.product_id.product_tmpl_id.enable_revenue_distribution
        )

        for line in candidate_lines:
            distribution_lines = line.product_id.product_tmpl_id.distribution_line_ids.filtered(
                lambda dist: dist.company_id == self.company_id
            ).sorted(key=lambda dist: (dist.sequence, dist.id))

            for dist in distribution_lines:
                distributed_amount = line.price_subtotal * (dist.percentage / 100.0)
                detail_commands.append((0, 0, {
                    'move_id': self.id,
                    'partner_id': self.partner_id.id,
                    'product_id': line.product_id.id,
                    'invoice_line_description': line.name,
                    'line_subtotal': line.price_subtotal,
                    'fund_box_id': dist.fund_box_id.id,
                    'percentage': dist.percentage,
                    'distributed_amount': distributed_amount,
                    'account_id': dist.account_id.id,
                    'analytic_account_id': dist.analytic_account_id.id,
                }))

                summary = summary_data.setdefault(dist.fund_box_id.id, {
                    'fund_box_id': dist.fund_box_id.id,
                    'total_distributed_amount': 0.0,
                    'account_id': dist.account_id.id,
                    'analytic_account_id': dist.analytic_account_id.id,
                })
                summary['total_distributed_amount'] += distributed_amount

        wizard = self.env['revenue.distribution.analysis.wizard'].create({
            'move_id': self.id,
            'detail_line_ids': detail_commands,
            'summary_line_ids': [(0, 0, vals) for vals in summary_data.values()],
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'تحليل توزيع الإيرادات',
            'res_model': 'revenue.distribution.analysis.wizard',
            'view_mode': 'form',
            'views': [(self.env.ref('syndicate_revenue_distribution.view_revenue_distribution_analysis_wizard_form').id, 'form')],
            'res_id': wizard.id,
            'target': 'new',
        }

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

    def _create_revenue_distribution_ledger(self):
        Ledger = self.env['syndicate.revenue.distribution.ledger.line']
        for move in self:
            if move.move_type not in ('out_invoice', 'out_refund'):
                continue

            existing_ledger = Ledger.search_count([
                ('move_id', '=', move.id),
                ('ledger_source', '=', 'invoice_post'),
            ])
            if existing_ledger:
                continue

            generated_lines = move.invoice_line_ids.filtered(
                lambda line:
                    line.is_distribution_generated
                    and line.fund_box_id
                    and line.distribution_percentage
                    and line.distribution_source_product_id
            )

            ledger_vals = []
            for line in generated_lines:
                percentage = line.distribution_percentage
                source_line = line.distribution_source_line_id
                product = line.distribution_source_product_id
                fund_box = line.fund_box_id
                account = line.account_id
                analytic_account = fund_box.analytic_account_id
                original_amount = (
                    source_line.price_subtotal
                    if source_line and not move.currency_id.is_zero(source_line.price_subtotal)
                    else line.price_subtotal * 100.0 / percentage
                )
                ledger_vals.append({
                    'move_id': move.id,
                    'journal_entry_id': move.id,
                    'move_line_id': line.id,
                    'source_move_line_id': source_line.id,
                    'invoice_date': move.invoice_date,
                    'partner_id': move.partner_id.id,
                    'product_id': product.id,
                    'product_tmpl_id': product.product_tmpl_id.id,
                    'fund_box_id': fund_box.id,
                    'account_id': account.id,
                    'analytic_account_id': analytic_account.id,
                    'percentage': percentage,
                    'original_amount': original_amount,
                    'distributed_amount': line.price_subtotal,
                    'company_id': move.company_id.id,
                    'currency_id': move.currency_id.id,
                    'state': 'posted',
                    'ledger_source': 'invoice_post',
                    'distribution_source': 'product',
                    'invoice_number_snapshot': move.name or '',
                    'partner_name_snapshot': move.partner_id.name or '',
                    'partner_ref_snapshot': move.partner_id.ref or '',
                    'product_name_snapshot': product.name or '',
                    'product_default_code_snapshot': product.default_code or '',
                    'product_type_snapshot': (
                        product.type
                        if 'type' in product._fields
                        else product.product_tmpl_id.detailed_type
                        if 'detailed_type' in product.product_tmpl_id._fields
                        else ''
                    ),
                    'fund_box_code_snapshot': (
                        fund_box.code if 'code' in fund_box._fields else ''
                    ),
                    'fund_box_name_snapshot': fund_box.name or '',
                    'account_code_snapshot': account.code or '',
                    'account_name_snapshot': account.name or '',
                    'analytic_account_name_snapshot': analytic_account.name or '',
                    'company_name_snapshot': move.company_id.name or '',
                    'currency_name_snapshot': move.currency_id.name or '',
                    'currency_symbol_snapshot': move.currency_id.symbol or '',
                })

            if ledger_vals:
                Ledger.create(ledger_vals)

    def action_post(self):
        self._auto_generate_distribution_lines()
        result = super().action_post()
        self._create_revenue_distribution_ledger()
        return result
