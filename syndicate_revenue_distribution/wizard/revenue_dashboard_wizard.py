from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class SyndicateRevenueDashboardWizard(models.TransientModel):
    _name = 'syndicate.revenue.dashboard.wizard'
    _description = 'Revenue Dashboard'

    period_type = fields.Selection(
        [
            ('today', 'Today'),
            ('this_week', 'This Week'),
            ('this_month', 'This Month'),
            ('this_year', 'This Year'),
            ('custom', 'Custom'),
        ],
        string='Period',
        default='this_month',
        required=True,
    )
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: self._get_period_dates('this_month')[0],
    )
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=lambda self: self._get_period_dates('this_month')[1],
    )
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
    total_distributed_amount = fields.Monetary(
        string='Total Distributed Amount',
        currency_field='currency_id',
        readonly=True,
    )
    total_invoice_count = fields.Integer(string='Total Invoices', readonly=True)
    total_ledger_line_count = fields.Integer(string='Total Ledger Lines', readonly=True)
    total_fund_box_count = fields.Integer(string='Total Fund Boxes', readonly=True)
    total_product_count = fields.Integer(string='Total Products', readonly=True)
    fund_box_line_ids = fields.One2many(
        'syndicate.revenue.dashboard.fund.box.line',
        'wizard_id',
        string='Top Fund Boxes',
        readonly=True,
    )
    product_line_ids = fields.One2many(
        'syndicate.revenue.dashboard.product.line',
        'wizard_id',
        string='Top Products',
        readonly=True,
    )
    latest_line_ids = fields.One2many(
        'syndicate.revenue.dashboard.latest.line',
        'wizard_id',
        string='Latest Ledger Lines',
        readonly=True,
    )

    def _get_period_dates(self, period_type):
        today = fields.Date.context_today(self)
        if period_type == 'today':
            return today, today
        if period_type == 'this_week':
            start = today - timedelta(days=today.weekday())
            return start, start + timedelta(days=6)
        if period_type == 'this_month':
            start = today.replace(day=1)
            next_month = (
                start.replace(year=start.year + 1, month=1)
                if start.month == 12
                else start.replace(month=start.month + 1)
            )
            return start, next_month - timedelta(days=1)
        if period_type == 'this_year':
            return today.replace(month=1, day=1), today.replace(month=12, day=31)
        return self.date_from, self.date_to

    @api.onchange('period_type')
    def _onchange_period_type(self):
        if self.period_type and self.period_type != 'custom':
            self.date_from, self.date_to = self._get_period_dates(self.period_type)

    def _get_ledger_domain(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError("تاريخ البداية يجب أن يكون قبل أو يساوي تاريخ النهاية.")

        domain = [
            ('state', '=', 'posted'),
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        if self.fund_box_id:
            domain.append(('fund_box_id', '=', self.fund_box_id.id))
        if self.product_id:
            domain.append(('product_id', '=', self.product_id.id))
        if self.partner_id:
            domain.append(('partner_id', '=', self.partner_id.id))
        return domain

    def _snapshot_or_name(self, record, snapshot_value):
        return snapshot_value or record.name or ''

    def action_generate_dashboard(self):
        self.ensure_one()
        Ledger = self.env['syndicate.revenue.distribution.ledger.line']
        domain = self._get_ledger_domain()
        ledger_lines = Ledger.search(domain, order='invoice_date, id')
        latest_lines = Ledger.search(domain, order='invoice_date desc, id desc', limit=20)

        total_distributed_amount = sum(ledger_lines.mapped('distributed_amount'))
        invoice_ids = {line.move_id.id for line in ledger_lines if line.move_id}
        fund_box_ids = {line.fund_box_id.id for line in ledger_lines if line.fund_box_id}
        product_ids = {line.product_id.id for line in ledger_lines if line.product_id}

        fund_box_totals = {}
        product_totals = {}
        for ledger in ledger_lines:
            fund_box_key = ledger.fund_box_id.id or ledger.fund_box_name_snapshot or ledger.id
            fund_box_data = fund_box_totals.setdefault(fund_box_key, {
                'fund_box_id': ledger.fund_box_id.id,
                'fund_box_name': self._snapshot_or_name(
                    ledger.fund_box_id,
                    ledger.fund_box_name_snapshot,
                ),
                'amount': 0.0,
            })
            fund_box_data['amount'] += ledger.distributed_amount

            product_key = ledger.product_id.id or ledger.product_name_snapshot or ledger.id
            product_data = product_totals.setdefault(product_key, {
                'product_id': ledger.product_id.id,
                'product_name': self._snapshot_or_name(
                    ledger.product_id,
                    ledger.product_name_snapshot,
                ),
                'amount': 0.0,
            })
            product_data['amount'] += ledger.distributed_amount

        top_fund_boxes = sorted(
            fund_box_totals.values(),
            key=lambda vals: vals['amount'],
            reverse=True,
        )[:5]
        top_products = sorted(
            product_totals.values(),
            key=lambda vals: vals['amount'],
            reverse=True,
        )[:5]

        fund_box_commands = []
        for rank, vals in enumerate(top_fund_boxes, start=1):
            fund_box_commands.append((0, 0, {
                **vals,
                'rank': rank,
                'percentage_of_total': (
                    vals['amount'] / total_distributed_amount * 100.0
                    if total_distributed_amount
                    else 0.0
                ),
            }))

        product_commands = []
        for rank, vals in enumerate(top_products, start=1):
            product_commands.append((0, 0, {
                **vals,
                'rank': rank,
                'percentage_of_total': (
                    vals['amount'] / total_distributed_amount * 100.0
                    if total_distributed_amount
                    else 0.0
                ),
            }))

        latest_commands = []
        for ledger in latest_lines:
            latest_commands.append((0, 0, {
                'ledger_id': ledger.id,
                'invoice_date': ledger.invoice_date,
                'move_id': ledger.move_id.id,
                'partner_name': self._snapshot_or_name(
                    ledger.partner_id,
                    ledger.partner_name_snapshot,
                ),
                'product_name': self._snapshot_or_name(
                    ledger.product_id,
                    ledger.product_name_snapshot,
                ),
                'fund_box_name': self._snapshot_or_name(
                    ledger.fund_box_id,
                    ledger.fund_box_name_snapshot,
                ),
                'distributed_amount': ledger.distributed_amount,
            }))

        self.write({
            'total_distributed_amount': total_distributed_amount,
            'total_invoice_count': len(invoice_ids),
            'total_ledger_line_count': len(ledger_lines),
            'total_fund_box_count': len(fund_box_ids),
            'total_product_count': len(product_ids),
            'fund_box_line_ids': [(5, 0, 0)] + fund_box_commands,
            'product_line_ids': [(5, 0, 0)] + product_commands,
            'latest_line_ids': [(5, 0, 0)] + latest_commands,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Revenue Dashboard',
            'res_model': 'syndicate.revenue.dashboard.wizard',
            'view_mode': 'form',
            'views': [(self.env.ref(
                'syndicate_revenue_distribution.view_syndicate_revenue_dashboard_wizard_form'
            ).id, 'form')],
            'res_id': self.id,
            'target': 'new',
        }


class SyndicateRevenueDashboardFundBoxLine(models.TransientModel):
    _name = 'syndicate.revenue.dashboard.fund.box.line'
    _description = 'Revenue Dashboard Fund Box Line'
    _order = 'amount desc, id'

    wizard_id = fields.Many2one(
        'syndicate.revenue.dashboard.wizard',
        required=True,
        ondelete='cascade',
    )
    fund_box_id = fields.Many2one('syndicate.fund.box', string='Fund Box', readonly=True)
    rank = fields.Integer(string='#', readonly=True)
    fund_box_name = fields.Char(string='Fund Box', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    amount = fields.Monetary(string='Amount', currency_field='currency_id', readonly=True)
    percentage_of_total = fields.Float(
        string='Percentage of Total',
        digits=(16, 4),
        readonly=True,
    )


class SyndicateRevenueDashboardProductLine(models.TransientModel):
    _name = 'syndicate.revenue.dashboard.product.line'
    _description = 'Revenue Dashboard Product Line'
    _order = 'amount desc, id'

    wizard_id = fields.Many2one(
        'syndicate.revenue.dashboard.wizard',
        required=True,
        ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    rank = fields.Integer(string='#', readonly=True)
    product_name = fields.Char(string='Product', readonly=True)
    currency_id = fields.Many2one(
        'res.currency',
        related='wizard_id.currency_id',
        readonly=True,
    )
    amount = fields.Monetary(string='Amount', currency_field='currency_id', readonly=True)
    percentage_of_total = fields.Float(
        string='Percentage of Total',
        digits=(16, 4),
        readonly=True,
    )


class SyndicateRevenueDashboardLatestLine(models.TransientModel):
    _name = 'syndicate.revenue.dashboard.latest.line'
    _description = 'Revenue Dashboard Latest Ledger Line'
    _order = 'invoice_date desc, id desc'

    wizard_id = fields.Many2one(
        'syndicate.revenue.dashboard.wizard',
        required=True,
        ondelete='cascade',
    )
    ledger_id = fields.Many2one(
        'syndicate.revenue.distribution.ledger.line',
        string='Ledger',
        readonly=True,
    )
    invoice_date = fields.Date(string='Invoice Date', readonly=True)
    move_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    partner_name = fields.Char(string='Partner', readonly=True)
    product_name = fields.Char(string='Product', readonly=True)
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
