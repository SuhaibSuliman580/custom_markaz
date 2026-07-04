from calendar import monthrange
from io import BytesIO
import base64
import re

from odoo import fields, models
from odoo.exceptions import UserError

try:
    import xlsxwriter
except ImportError:
    xlsxwriter = None


class SyndicateRevenueAnalyticsWizard(models.TransientModel):
    _name = 'syndicate.revenue.analytics.wizard'
    _description = 'Revenue Analytics'

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
    )
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
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
    total_distributed_amount = fields.Monetary(
        string='Total Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        currency_field='currency_id',
        readonly=True,
    )
    total_invoice_count = fields.Integer(string='Total Invoices', readonly=True)
    total_ledger_line_count = fields.Integer(string='Total Ledger Lines', readonly=True)
    average_distribution_per_invoice = fields.Monetary(
        string='Average Distribution Per Invoice',
        currency_field='currency_id',
        readonly=True,
    )
    average_distribution_per_product = fields.Monetary(
        string='Average Distribution Per Product',
        currency_field='currency_id',
        readonly=True,
    )
    fund_box_line_ids = fields.One2many(
        'syndicate.revenue.analytics.fund.box.line',
        'wizard_id',
        string='Top 10 Fund Boxes',
        readonly=True,
    )
    product_line_ids = fields.One2many(
        'syndicate.revenue.analytics.product.line',
        'wizard_id',
        string='Top 10 Products',
        readonly=True,
    )
    partner_line_ids = fields.One2many(
        'syndicate.revenue.analytics.partner.line',
        'wizard_id',
        string='Top 10 Partners',
        readonly=True,
    )
    month_line_ids = fields.One2many(
        'syndicate.revenue.analytics.month.line',
        'wizard_id',
        string='Monthly Revenue Trend',
        readonly=True,
    )
    export_file = fields.Binary(string='Export File', readonly=True)
    export_filename = fields.Char(string='Export Filename', readonly=True)

    def _get_ledger_domain(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise UserError("تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية.")

        domain = [
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        if self.date_from:
            domain.append(('invoice_date', '>=', self.date_from))
        if self.date_to:
            domain.append(('invoice_date', '<=', self.date_to))
        if self.fund_box_id:
            domain.append(('fund_box_id', '=', self.fund_box_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return domain

    def _get_common_ledger_domain(self):
        self.ensure_one()
        domain = [
            ('state', '=', 'posted'),
            ('company_id', '=', self.company_id.id),
        ]
        if self.fund_box_id:
            domain.append(('fund_box_id', '=', self.fund_box_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return domain

    def _get_ledger_action(self, domain, name='Revenue Distribution Ledger'):
        action = self.env.ref(
            'syndicate_revenue_distribution.action_revenue_distribution_ledger_line'
        ).read()[0]
        action.update({
            'name': name,
            'domain': domain,
            'view_mode': 'tree,form',
            'target': 'current',
        })
        return action

    def _snapshot_or_name(self, record, snapshot_value):
        return snapshot_value or record.name or ''

    def _revenue_key_and_amount(self, ledger):
        if ledger.source_move_line_id:
            return ('source', ledger.source_move_line_id.id), ledger.original_amount
        return ('ledger', ledger.id), ledger.distributed_amount

    def _ranking_commands(self, grouped_values, total_distributed_amount):
        commands = []
        top_values = sorted(
            grouped_values.values(),
            key=lambda vals: vals['distributed_amount'],
            reverse=True,
        )[:10]
        for rank, vals in enumerate(top_values, start=1):
            commands.append((0, 0, {
                **vals,
                'rank': rank,
                'percentage_of_total': (
                    vals['distributed_amount'] / total_distributed_amount * 100.0
                    if total_distributed_amount
                    else 0.0
                ),
            }))
        return commands

    def _get_generated_at_text(self):
        self.ensure_one()
        generated_at = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        return generated_at.strftime('%Y-%m-%d %H:%M:%S')

    def _get_export_company_name(self):
        self.ensure_one()
        return self.company_id.name or 'Company'

    def _get_export_filename_base(self):
        self.ensure_one()
        company = re.sub(r'[^A-Za-z0-9_-]+', '_', self._get_export_company_name()).strip('_')
        today = fields.Date.context_today(self).strftime('%Y%m%d')
        return f"Revenue_Analytics_{company or 'Company'}_{today}"

    def _ensure_analytics_generated(self):
        self.ensure_one()
        self.action_generate_analytics()

    def _write_excel_title(self, worksheet, title, workbook, last_col=4):
        title_format = workbook.add_format({
            'bold': True,
            'font_size': 14,
            'align': 'center',
            'valign': 'vcenter',
            'bg_color': '#D9EAF7',
            'border': 1,
        })
        worksheet.merge_range(0, 0, 0, last_col, title, title_format)

    def _write_excel_metadata(self, worksheet, workbook):
        label_format = workbook.add_format({'bold': True, 'bg_color': '#F2F2F2', 'border': 1})
        value_format = workbook.add_format({'border': 1})
        rows = [
            ('Generated At', self._get_generated_at_text()),
            ('Company', self.company_id.name or ''),
            ('Date From', str(self.date_from or '')),
            ('Date To', str(self.date_to or '')),
            ('Fund Box', self.fund_box_id.name or ''),
            ('Product', self.product_id.name or ''),
            ('Partner', self.partner_id.name or ''),
        ]
        for row_idx, (label, value) in enumerate(rows, start=2):
            worksheet.write(row_idx, 0, label, label_format)
            worksheet.write(row_idx, 1, value, value_format)

    def _write_excel_table(self, worksheet, workbook, start_row, headers, rows):
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#0F6B7A',
            'font_color': 'white',
            'border': 1,
            'align': 'center',
        })
        text_format = workbook.add_format({'border': 1})
        money_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        percent_format = workbook.add_format({'border': 1, 'num_format': '0.00%'})
        integer_format = workbook.add_format({'border': 1, 'num_format': '0'})
        widths = [len(header) for header, _field, _kind in headers]

        for col, (header, _field, _kind) in enumerate(headers):
            worksheet.write(start_row, col, header, header_format)

        for row_offset, row_data in enumerate(rows, start=1):
            for col, (_header, field_name, kind) in enumerate(headers):
                value = row_data.get(field_name, '')
                if kind == 'money':
                    worksheet.write_number(start_row + row_offset, col, value or 0.0, money_format)
                    display_value = f"{value or 0.0:.2f}"
                elif kind == 'percent':
                    worksheet.write_number(start_row + row_offset, col, (value or 0.0) / 100.0, percent_format)
                    display_value = f"{value or 0.0:.2f}%"
                elif kind == 'integer':
                    worksheet.write_number(start_row + row_offset, col, value or 0, integer_format)
                    display_value = str(value or 0)
                else:
                    worksheet.write(start_row + row_offset, col, value or '', text_format)
                    display_value = str(value or '')
                widths[col] = max(widths[col], len(display_value))

        for col, width in enumerate(widths):
            worksheet.set_column(col, col, min(max(width + 2, 12), 42))
        worksheet.freeze_panes(start_row + 1, 0)

    def action_export_excel(self):
        self.ensure_one()
        if not xlsxwriter:
            raise UserError("مكتبة xlsxwriter غير متاحة على الخادم.")

        self._ensure_analytics_generated()
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})

        kpi_sheet = workbook.add_worksheet('Executive KPIs')
        self._write_excel_title(kpi_sheet, 'Executive KPIs', workbook, 2)
        self._write_excel_metadata(kpi_sheet, workbook)
        self._write_excel_table(kpi_sheet, workbook, 11, [
            ('KPI', 'kpi', 'text'),
            ('Value', 'value', 'money'),
        ], [
            {'kpi': 'Total Distributed Amount', 'value': self.total_distributed_amount},
            {'kpi': 'Total Revenue', 'value': self.total_revenue},
            {'kpi': 'Average Distribution Per Invoice', 'value': self.average_distribution_per_invoice},
            {'kpi': 'Average Distribution Per Product', 'value': self.average_distribution_per_product},
        ])
        self._write_excel_table(kpi_sheet, workbook, 18, [
            ('KPI', 'kpi', 'text'),
            ('Value', 'value', 'integer'),
        ], [
            {'kpi': 'Total Invoices', 'value': self.total_invoice_count},
            {'kpi': 'Total Ledger Lines', 'value': self.total_ledger_line_count},
        ])

        sheet_specs = [
            ('Top Fund Boxes', [
                ('Rank', 'rank', 'integer'),
                ('Fund Box', 'name', 'text'),
                ('Distributed Amount', 'amount', 'money'),
                ('Percentage of Total', 'percentage', 'percent'),
            ], [
                {
                    'rank': line.rank,
                    'name': line.fund_box_name,
                    'amount': line.distributed_amount,
                    'percentage': line.percentage_of_total,
                }
                for line in self.fund_box_line_ids
            ]),
            ('Top Products', [
                ('Rank', 'rank', 'integer'),
                ('Product', 'name', 'text'),
                ('Distributed Amount', 'amount', 'money'),
                ('Percentage of Total', 'percentage', 'percent'),
            ], [
                {
                    'rank': line.rank,
                    'name': line.product_name,
                    'amount': line.distributed_amount,
                    'percentage': line.percentage_of_total,
                }
                for line in self.product_line_ids
            ]),
            ('Top Partners', [
                ('Rank', 'rank', 'integer'),
                ('Partner', 'name', 'text'),
                ('Distributed Amount', 'amount', 'money'),
                ('Percentage of Total', 'percentage', 'percent'),
            ], [
                {
                    'rank': line.rank,
                    'name': line.partner_name,
                    'amount': line.distributed_amount,
                    'percentage': line.percentage_of_total,
                }
                for line in self.partner_line_ids
            ]),
            ('Monthly Revenue Trend', [
                ('Month', 'month', 'text'),
                ('Revenue', 'revenue', 'money'),
                ('Distributed Amount', 'amount', 'money'),
                ('Invoice Count', 'invoice_count', 'integer'),
            ], [
                {
                    'month': line.month,
                    'revenue': line.revenue,
                    'amount': line.distributed_amount,
                    'invoice_count': line.invoice_count,
                }
                for line in self.month_line_ids
            ]),
        ]
        for sheet_name, headers, rows in sheet_specs:
            worksheet = workbook.add_worksheet(sheet_name)
            self._write_excel_title(worksheet, sheet_name, workbook, len(headers) - 1)
            self._write_excel_metadata(worksheet, workbook)
            self._write_excel_table(worksheet, workbook, 11, headers, rows)

        workbook.close()
        output.seek(0)
        filename = f"{self._get_export_filename_base()}.xlsx"
        self.write({
            'export_file': base64.b64encode(output.read()),
            'export_filename': filename,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': (
                '/web/content/?model=syndicate.revenue.analytics.wizard'
                f'&id={self.id}&field=export_file&filename_field=export_filename'
                '&download=true'
            ),
            'target': 'self',
        }

    def action_export_pdf(self):
        self.ensure_one()
        self._ensure_analytics_generated()
        return self.env.ref(
            'syndicate_revenue_distribution.action_report_revenue_analytics'
        ).report_action(self)

    def _get_report_base_filename(self):
        return self._get_export_filename_base()

    def action_generate_analytics(self):
        self.ensure_one()
        Ledger = self.env['syndicate.revenue.distribution.ledger.line']
        ledger_lines = Ledger.search(
            self._get_ledger_domain(),
            order='invoice_date, id',
        )

        total_distributed_amount = sum(ledger_lines.mapped('distributed_amount'))
        invoice_ids = {line.move_id.id for line in ledger_lines if line.move_id}
        product_ids = {line.product_id.id for line in ledger_lines if line.product_id}

        revenue_source_keys = set()
        total_revenue = 0.0
        fund_box_totals = {}
        product_totals = {}
        partner_totals = {}
        monthly_totals = {}

        for ledger in ledger_lines:
            revenue_key, revenue_amount = self._revenue_key_and_amount(ledger)
            if revenue_key not in revenue_source_keys:
                total_revenue += revenue_amount
                revenue_source_keys.add(revenue_key)

            fund_box_key = ledger.fund_box_id.id or ledger.fund_box_name_snapshot or ledger.id
            fund_box_data = fund_box_totals.setdefault(fund_box_key, {
                'fund_box_id': ledger.fund_box_id.id,
                'fund_box_name': self._snapshot_or_name(
                    ledger.fund_box_id,
                    ledger.fund_box_name_snapshot,
                ),
                'distributed_amount': 0.0,
            })
            fund_box_data['distributed_amount'] += ledger.distributed_amount

            product_key = ledger.product_id.id or ledger.product_name_snapshot or ledger.id
            product_data = product_totals.setdefault(product_key, {
                'product_id': ledger.product_id.id,
                'product_name': self._snapshot_or_name(
                    ledger.product_id,
                    ledger.product_name_snapshot,
                ),
                'distributed_amount': 0.0,
            })
            product_data['distributed_amount'] += ledger.distributed_amount

            partner_key = ledger.partner_id.id or ledger.partner_name_snapshot or ledger.id
            partner_data = partner_totals.setdefault(partner_key, {
                'partner_id': ledger.partner_id.id,
                'partner_name': self._snapshot_or_name(
                    ledger.partner_id,
                    ledger.partner_name_snapshot,
                ),
                'distributed_amount': 0.0,
            })
            partner_data['distributed_amount'] += ledger.distributed_amount

            if ledger.invoice_date:
                month_key = ledger.invoice_date.strftime('%Y-%m')
                month_data = monthly_totals.setdefault(month_key, {
                    'month_key': month_key,
                    'month': ledger.invoice_date.strftime('%Y-%m'),
                    'revenue': 0.0,
                    'distributed_amount': 0.0,
                    'invoice_ids': set(),
                    'revenue_source_keys': set(),
                })
                month_data['distributed_amount'] += ledger.distributed_amount
                if ledger.move_id:
                    month_data['invoice_ids'].add(ledger.move_id.id)
                if revenue_key not in month_data['revenue_source_keys']:
                    month_data['revenue'] += revenue_amount
                    month_data['revenue_source_keys'].add(revenue_key)

        month_commands = []
        for month_key in sorted(monthly_totals):
            vals = monthly_totals[month_key]
            month_commands.append((0, 0, {
                'month_key': vals['month_key'],
                'month': vals['month'],
                'revenue': vals['revenue'],
                'distributed_amount': vals['distributed_amount'],
                'invoice_count': len(vals['invoice_ids']),
            }))

        self.write({
            'total_distributed_amount': total_distributed_amount,
            'total_revenue': total_revenue,
            'total_invoice_count': len(invoice_ids),
            'total_ledger_line_count': len(ledger_lines),
            'average_distribution_per_invoice': (
                total_distributed_amount / len(invoice_ids)
                if invoice_ids
                else 0.0
            ),
            'average_distribution_per_product': (
                total_distributed_amount / len(product_ids)
                if product_ids
                else 0.0
            ),
            'fund_box_line_ids': [(5, 0, 0)] + self._ranking_commands(
                fund_box_totals,
                total_distributed_amount,
            ),
            'product_line_ids': [(5, 0, 0)] + self._ranking_commands(
                product_totals,
                total_distributed_amount,
            ),
            'partner_line_ids': [(5, 0, 0)] + self._ranking_commands(
                partner_totals,
                total_distributed_amount,
            ),
            'month_line_ids': [(5, 0, 0)] + month_commands,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Revenue Analytics',
            'res_model': 'syndicate.revenue.analytics.wizard',
            'view_mode': 'form',
            'views': [(self.env.ref(
                'syndicate_revenue_distribution.view_syndicate_revenue_analytics_wizard_form'
            ).id, 'form')],
            'res_id': self.id,
            'target': 'new',
        }


class SyndicateRevenueAnalyticsFundBoxLine(models.TransientModel):
    _name = 'syndicate.revenue.analytics.fund.box.line'
    _description = 'Revenue Analytics Fund Box Line'
    _order = 'rank, id'

    wizard_id = fields.Many2one(
        'syndicate.revenue.analytics.wizard',
        required=True,
        ondelete='cascade',
    )
    rank = fields.Integer(string='Rank', readonly=True)
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True)
    fund_box_name = fields.Char(string='Fund Box', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    distributed_amount = fields.Monetary(
        string='Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    percentage_of_total = fields.Float(
        string='Percentage of Total',
        digits=(16, 2),
        readonly=True,
    )

    def action_open_ledger(self):
        self.ensure_one()
        domain = self.wizard_id._get_ledger_domain()
        if self.fund_box_id:
            domain.append(('fund_box_id', '=', self.fund_box_id.id))
        else:
            domain.append(('fund_box_name_snapshot', '=', self.fund_box_name))
        return self.wizard_id._get_ledger_action(
            domain,
            name='Revenue Distribution Ledger - Fund Box',
        )


class SyndicateRevenueAnalyticsProductLine(models.TransientModel):
    _name = 'syndicate.revenue.analytics.product.line'
    _description = 'Revenue Analytics Product Line'
    _order = 'rank, id'

    wizard_id = fields.Many2one(
        'syndicate.revenue.analytics.wizard',
        required=True,
        ondelete='cascade',
    )
    rank = fields.Integer(string='Rank', readonly=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_name = fields.Char(string='Product', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    distributed_amount = fields.Monetary(
        string='Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    percentage_of_total = fields.Float(
        string='Percentage of Total',
        digits=(16, 2),
        readonly=True,
    )

    def action_open_ledger(self):
        self.ensure_one()
        domain = self.wizard_id._get_ledger_domain()
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        else:
            domain.append(('product_name_snapshot', '=', self.product_name))
        return self.wizard_id._get_ledger_action(
            domain,
            name='Revenue Distribution Ledger - Product',
        )


class SyndicateRevenueAnalyticsPartnerLine(models.TransientModel):
    _name = 'syndicate.revenue.analytics.partner.line'
    _description = 'Revenue Analytics Partner Line'
    _order = 'rank, id'

    wizard_id = fields.Many2one(
        'syndicate.revenue.analytics.wizard',
        required=True,
        ondelete='cascade',
    )
    rank = fields.Integer(string='Rank', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    partner_name = fields.Char(string='Partner', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    distributed_amount = fields.Monetary(
        string='Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    percentage_of_total = fields.Float(
        string='Percentage of Total',
        digits=(16, 2),
        readonly=True,
    )

    def action_open_ledger(self):
        self.ensure_one()
        domain = self.wizard_id._get_ledger_domain()
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        else:
            domain.append(('partner_name_snapshot', '=', self.partner_name))
        return self.wizard_id._get_ledger_action(
            domain,
            name='Revenue Distribution Ledger - Partner',
        )


class SyndicateRevenueAnalyticsMonthLine(models.TransientModel):
    _name = 'syndicate.revenue.analytics.month.line'
    _description = 'Revenue Analytics Month Line'
    _order = 'month_key, id'

    wizard_id = fields.Many2one(
        'syndicate.revenue.analytics.wizard',
        required=True,
        ondelete='cascade',
    )
    month_key = fields.Char(string='Month Key', readonly=True)
    month = fields.Char(string='Month', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    revenue = fields.Monetary(
        string='Revenue',
        currency_field='currency_id',
        readonly=True,
    )
    distributed_amount = fields.Monetary(
        string='Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    invoice_count = fields.Integer(string='Invoice Count', readonly=True)

    def action_open_ledger(self):
        self.ensure_one()
        year, month = (int(part) for part in self.month_key.split('-'))
        last_day = monthrange(year, month)[1]
        domain = self.wizard_id._get_common_ledger_domain()
        domain += [
            ('invoice_date', '>=', f'{year:04d}-{month:02d}-01'),
            ('invoice_date', '<=', f'{year:04d}-{month:02d}-{last_day:02d}'),
        ]
        return self.wizard_id._get_ledger_action(
            domain,
            name='Revenue Distribution Ledger - Month',
        )
