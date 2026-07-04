from odoo import fields, models
from odoo.exceptions import UserError


class RevenueDistributionReportWizard(models.TransientModel):
    _name = 'revenue.distribution.report.wizard'
    _description = 'Revenue Distribution Report'

    date_from = fields.Date(string='Date From', required=True)
    date_to = fields.Date(string='Date To', required=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    fund_box_id = fields.Many2one(
        'syndicate.fund.box',
        string='Fund Box',
        domain="[('company_id', '=', company_id)]",
    )
    product_id = fields.Many2one('product.product', string='Product')
    partner_id = fields.Many2one('res.partner', string='Partner')
    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        related='company_id.currency_id',
        readonly=True,
    )
    line_ids = fields.One2many(
        'revenue.distribution.report.line',
        'wizard_id',
        string='Details',
        readonly=True,
    )
    summary_line_ids = fields.One2many(
        'revenue.distribution.report.summary.line',
        'wizard_id',
        string='Summary by Fund Box',
        readonly=True,
    )
    result_message = fields.Text(string='Result', readonly=True)
    detail_count = fields.Integer(
        string='Detail Lines',
        compute='_compute_result_counts',
    )
    summary_count = fields.Integer(
        string='Summary Lines',
        compute='_compute_result_counts',
    )
    total_invoice_count = fields.Integer(string='Total Invoices', readonly=True)
    total_revenue = fields.Monetary(
        string='Total Revenue',
        currency_field='currency_id',
        readonly=True,
    )
    total_distributed_amount = fields.Monetary(
        string='Total Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )

    def _compute_result_counts(self):
        for rec in self:
            rec.detail_count = len(rec.line_ids)
            rec.summary_count = len(rec.summary_line_ids)

    def action_generate_report(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError("تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية.")

        self.line_ids.unlink()
        self.summary_line_ids.unlink()

        ledger_domain = [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
            ('ledger_source', 'in', ('invoice_post', 'reversal')),
        ]
        if self.fund_box_id:
            ledger_domain.append(('fund_box_id', '=', self.fund_box_id.id))
        if self.product_id:
            ledger_domain.append(('product_id', '=', self.product_id.id))
        if self.partner_id:
            ledger_domain.append(('partner_id', '=', self.partner_id.id))

        ledger_lines = self.env['syndicate.revenue.distribution.ledger.line'].search(
            ledger_domain,
            order='invoice_date, move_id, id',
        )

        detail_commands = []
        summary_data = {}
        invoice_ids = set()
        revenue_source_keys = set()
        total_revenue = 0.0

        for ledger in ledger_lines:
            partner_name = ledger.partner_name_snapshot or ledger.partner_id.name or ''
            product_name = ledger.product_name_snapshot or ledger.product_id.name or ''
            fund_box_name = ledger.fund_box_name_snapshot or ledger.fund_box_id.name or ''

            detail_commands.append((0, 0, {
                'move_id': ledger.move_id.id,
                'invoice_date': ledger.invoice_date,
                'partner_id': ledger.partner_id.id,
                'partner_name': partner_name,
                'product_id': ledger.product_id.id,
                'product_display_name': product_name,
                'fund_box_id': ledger.fund_box_id.id,
                'fund_box_name': fund_box_name,
                'percentage': ledger.percentage,
                'original_amount': ledger.original_amount,
                'distributed_amount': ledger.distributed_amount,
                'account_id': ledger.account_id.id,
                'analytic_account_id': ledger.analytic_account_id.id,
                'company_id': ledger.company_id.id,
            }))

            summary_key = ledger.fund_box_id.id or ledger.fund_box_name_snapshot or ledger.id
            summary = summary_data.setdefault(summary_key, {
                'fund_box_id': ledger.fund_box_id.id,
                'fund_box_name': fund_box_name,
                'total_distributed_amount': 0.0,
                'account_id': ledger.account_id.id,
                'analytic_account_id': ledger.analytic_account_id.id,
            })
            summary['total_distributed_amount'] += ledger.distributed_amount

            if ledger.move_id:
                invoice_ids.add(ledger.move_id.id)

            source_key = (
                ledger.source_move_line_id.id
                if ledger.source_move_line_id
                else ledger.move_line_id.id
                if ledger.move_line_id
                else ledger.id
            )
            if source_key not in revenue_source_keys:
                total_revenue += (
                    ledger.original_amount
                    if ledger.source_move_line_id
                    else ledger.distributed_amount
                )
                revenue_source_keys.add(source_key)

        total_distributed_amount = sum(
            vals['total_distributed_amount']
            for vals in summary_data.values()
        )
        for vals in summary_data.values():
            vals['percentage_of_total'] = (
                vals['total_distributed_amount'] / total_distributed_amount * 100.0
                if total_distributed_amount
                else 0.0
            )

        result_message = (
            "تم إنشاء التقرير من دفتر توزيع الإيرادات. افتح تبويب Details أو Summary by Fund Box لعرض النتائج."
            if detail_commands
            else "لا توجد سجلات دفتر توزيع الإيرادات للفترة المحددة."
        )

        self.write({
            'line_ids': detail_commands,
            'summary_line_ids': [(0, 0, vals) for vals in summary_data.values()],
            'result_message': result_message,
            'total_invoice_count': len(invoice_ids),
            'total_revenue': total_revenue,
            'total_distributed_amount': total_distributed_amount,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'تقرير توزيع الإيرادات',
            'res_model': 'revenue.distribution.report.wizard',
            'view_mode': 'form',
            'views': [(self.env.ref('syndicate_revenue_distribution.view_revenue_distribution_report_wizard_form').id, 'form')],
            'res_id': self.id,
            'target': 'new',
        }


class RevenueDistributionReportLine(models.TransientModel):
    _name = 'revenue.distribution.report.line'
    _description = 'Revenue Distribution Report Line'
    _order = 'invoice_date, move_id, id'

    wizard_id = fields.Many2one(
        'revenue.distribution.report.wizard',
        required=True,
        ondelete='cascade',
    )
    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    invoice_date = fields.Date(string='Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char(string='Partner Name', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_display_name = fields.Char(string='Product', readonly=True)
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True)
    fund_box_name = fields.Char(string='Fund Box', readonly=True)
    percentage = fields.Float(string='Percentage', digits=(16, 4), readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    original_amount = fields.Monetary(
        string='Original Amount',
        currency_field='currency_id',
        readonly=True,
    )
    distributed_amount = fields.Monetary(
        string='Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    account_id = fields.Many2one('account.account', string='Income Account', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
    )
    company_id = fields.Many2one('res.company', string='Company', readonly=True)


class RevenueDistributionReportSummaryLine(models.TransientModel):
    _name = 'revenue.distribution.report.summary.line'
    _description = 'Revenue Distribution Report Summary Line'
    _order = 'fund_box_id, id'

    wizard_id = fields.Many2one(
        'revenue.distribution.report.wizard',
        required=True,
        ondelete='cascade',
    )
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True)
    fund_box_name = fields.Char(string='Fund Box', readonly=True)
    total_distributed_amount = fields.Monetary(
        string='Total Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    percentage_of_total = fields.Float(
        string='Percentage of Total',
        digits=(16, 4),
        readonly=True,
    )
    account_id = fields.Many2one('account.account', string='Income Account', readonly=True)
    analytic_account_id = fields.Many2one(
        'account.analytic.account',
        string='Analytic Account',
        readonly=True,
    )
