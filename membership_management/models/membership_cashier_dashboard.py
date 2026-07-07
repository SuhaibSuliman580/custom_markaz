from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MembershipCashierDashboard(models.TransientModel):
    _name = 'membership.cashier.dashboard'
    _description = 'قبض فواتير خدمات الأطباء'
    _rec_name = 'name'

    name = fields.Char(string='العنوان', default='قبض فواتير خدمات الأطباء', readonly=True)
    date_filter = fields.Selection([
        ('today', 'اليوم'),
        ('yesterday', 'أمس'),
        ('week', 'هذا الأسبوع'),
        ('month', 'هذا الشهر'),
        ('custom', 'فترة مخصصة'),
    ], string='الفترة', default='today')
    date_from = fields.Date(string='من تاريخ')
    date_to = fields.Date(string='إلى تاريخ')
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    allowed_cash_journal_ids = fields.Many2many(
        'account.journal',
        string='دفاتر اليومية النقدية المسموحة',
        readonly=True,
    )
    allowed_cash_journal_count = fields.Integer(string='عدد دفاتر اليومية النقدية', readonly=True)
    has_cash_journals = fields.Boolean(string='لديه دفاتر يومية نقدية', readonly=True)
    has_pending_invoices = fields.Boolean(string='توجد فواتير بانتظار القبض', readonly=True)
    today_receipts = fields.Monetary(
        string='إجمالي المقبوضات',
        currency_field='currency_id',
        readonly=True,
    )
    today_paid_invoice_count = fields.Integer(string='عدد الفواتير المقبوضة', readonly=True)
    pending_residual_total = fields.Monetary(
        string='إجمالي المتبقي بانتظار القبض',
        currency_field='currency_id',
        readonly=True,
    )
    receipt_summary_line_ids = fields.One2many(
        'membership.cashier.receipt.summary.line',
        'dashboard_id',
        string='حصيلة القبض حسب دفتر اليومية',
        readonly=True,
    )
    invoice_line_ids = fields.One2many(
        'membership.cashier.invoice.line',
        'dashboard_id',
        string='فواتير بانتظار القبض',
        readonly=True,
    )
    paid_invoice_line_ids = fields.One2many(
        'membership.cashier.paid.invoice.line',
        'dashboard_id',
        string='فواتير مقبوضة',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        date_filter, date_from, date_to = self._get_context_period_defaults()
        vals.update({
            'name': _('قبض فواتير خدمات الأطباء'),
            'date_filter': date_filter,
            'date_from': date_from,
            'date_to': date_to,
        })
        vals.update(self._prepare_dashboard_values(date_filter, date_from, date_to))
        return vals

    @api.model
    def action_open_dashboard(self):
        date_filter, date_from, date_to = self._get_context_period_defaults()
        vals = {
            'name': _('قبض فواتير خدمات الأطباء'),
            'date_filter': date_filter,
            'date_from': date_from,
            'date_to': date_to,
        }
        vals.update(self._prepare_dashboard_values(date_filter, date_from, date_to))
        dashboard = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('قبض فواتير خدمات الأطباء'),
            'res_model': 'membership.cashier.dashboard',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'membership_management.view_membership_cashier_dashboard_form'
            ).id,
            'target': 'current',
        }

    @api.model
    def _get_context_period_defaults(self):
        today = fields.Date.context_today(self)
        date_filter = self.env.context.get('cashier_dashboard_date_filter') or 'today'
        date_from = self.env.context.get('cashier_dashboard_date_from')
        date_to = self.env.context.get('cashier_dashboard_date_to')
        if not date_from or not date_to:
            date_from, date_to = self._get_period_dates(date_filter, today, today)
        return date_filter, fields.Date.to_date(date_from), fields.Date.to_date(date_to)

    @api.model
    def _get_period_dates(self, date_filter, date_from=False, date_to=False):
        today = fields.Date.context_today(self)
        if date_filter == 'yesterday':
            day = today - timedelta(days=1)
            return day, day
        if date_filter == 'week':
            return today - timedelta(days=today.weekday()), today
        if date_filter == 'month':
            return today.replace(day=1), today
        if date_filter == 'custom':
            start = fields.Date.to_date(date_from) if date_from else today
            stop = fields.Date.to_date(date_to) if date_to else start
            if stop < start:
                raise UserError(_('تاريخ النهاية يجب أن يكون بعد تاريخ البداية أو مساوياً له.'))
            return start, stop
        return today, today

    def _refresh_dashboard_with_period(self, date_filter, date_from=False, date_to=False):
        for dashboard in self:
            start, stop = dashboard._get_period_dates(date_filter, date_from, date_to)
            vals = {
                'date_filter': date_filter,
                'date_from': start,
                'date_to': stop,
            }
            vals.update(dashboard._prepare_dashboard_values(date_filter, start, stop))
            vals['receipt_summary_line_ids'] = [(5, 0, 0)] + vals.get('receipt_summary_line_ids', [])
            vals['invoice_line_ids'] = [(5, 0, 0)] + vals.get('invoice_line_ids', [])
            vals['paid_invoice_line_ids'] = [(5, 0, 0)] + vals.get('paid_invoice_line_ids', [])
            dashboard.write(vals)
        return True

    def action_refresh_dashboard(self):
        for dashboard in self:
            dashboard._refresh_dashboard_with_period(
                dashboard.date_filter or 'today',
                dashboard.date_from,
                dashboard.date_to,
            )
        return True

    def action_filter_today(self):
        return self._refresh_dashboard_with_period('today')

    def action_filter_yesterday(self):
        return self._refresh_dashboard_with_period('yesterday')

    def action_filter_week(self):
        return self._refresh_dashboard_with_period('week')

    def action_filter_month(self):
        return self._refresh_dashboard_with_period('month')

    def action_apply_custom_period(self):
        for dashboard in self:
            dashboard._refresh_dashboard_with_period('custom', dashboard.date_from, dashboard.date_to)
        return True

    @api.model
    def _get_allowed_cash_journals(self):
        journals = self.env.user.allowed_cash_journal_ids.filtered(
            lambda journal: journal.type == 'cash' and journal.company_id in self.env.companies
        )
        if self.env.user.has_group('membership_management.group_membership_service_manager') and not journals:
            journals = self.env['account.journal'].search([
                ('type', '=', 'cash'),
                ('company_id', 'in', self.env.companies.ids),
            ])
        return journals

    @api.model
    def _get_pending_invoice_domain(self):
        return [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('payment_state', 'in', ('not_paid', 'partial')),
            ('amount_residual', '>', 0),
            ('membership_service_request_id', '!=', False),
            ('company_id', 'in', self.env.companies.ids),
        ]

    @api.model
    def _get_date_bounds_utc(self, date_from, date_to):
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        start_local = user_tz.localize(datetime.combine(date_from, time.min))
        stop_local = user_tz.localize(datetime.combine(date_to + timedelta(days=1), time.min))
        return (
            start_local.astimezone(pytz.UTC).replace(tzinfo=None),
            stop_local.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    @api.model
    def _prepare_dashboard_values(self, date_filter='today', date_from=False, date_to=False):
        date_from, date_to = self._get_period_dates(date_filter, date_from, date_to)
        _start_utc, _stop_utc = self._get_date_bounds_utc(date_from, date_to)
        journals = self._get_allowed_cash_journals()
        currency = self.env.company.currency_id

        pending_invoices = self.env['account.move'].search(
            self._get_pending_invoice_domain(),
            order='invoice_date desc, name desc, id desc',
        )
        pending_period_invoices = pending_invoices.filtered(
            lambda invoice: date_from <= (invoice.invoice_date or fields.Date.context_today(self)) <= date_to
        )
        pending_residual_total = sum(pending_period_invoices.mapped('amount_residual'))

        summary_by_journal = {}
        total_receipts = 0.0
        paid_invoice_ids = set()
        paid_invoice_line_commands = []

        if journals:
            liquidity_accounts = journals.mapped('default_account_id')
            receipt_lines = self.env['account.move.line'].search([
                ('parent_state', '=', 'posted'),
                ('company_id', 'in', self.env.companies.ids),
                ('journal_id', 'in', journals.ids),
                ('account_id', 'in', liquidity_accounts.ids),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
                ('debit', '>', 0),
            ])
            for line in receipt_lines:
                data = summary_by_journal.setdefault(line.journal_id.id, {
                    'journal_id': line.journal_id.id,
                    'amount': 0.0,
                    'payment_count': 0,
                })
                amount = line.company_currency_id._convert(
                    line.debit,
                    currency,
                    line.company_id,
                    line.date,
                )
                data['amount'] += amount
                total_receipts += amount
                data['payment_count'] += 1

            payment_domain = [
                ('state', '=', 'posted'),
                ('payment_type', '=', 'inbound'),
                ('journal_id', 'in', journals.ids),
                ('company_id', 'in', self.env.companies.ids),
                ('date', '>=', date_from),
                ('date', '<=', date_to),
            ]
            if not self.env.user.has_group('membership_management.group_membership_service_manager'):
                payment_domain.append(('create_uid', '=', self.env.user.id))
            payments = self.env['account.payment'].search(payment_domain, order='date desc, name desc, id desc')
            for payment in payments:
                invoices = payment.reconciled_invoice_ids.filtered(
                    lambda invoice: (
                        invoice.move_type == 'out_invoice'
                        and invoice.membership_service_request_id
                        and invoice.company_id in self.env.companies
                    )
                )
                for invoice in invoices:
                    request = invoice.membership_service_request_id
                    paid_invoice_ids.add(invoice.id)
                    paid_invoice_line_commands.append((0, 0, {
                        'payment_id': payment.id,
                        'invoice_id': invoice.id,
                        'service_request_id': request.id,
                        'partner_id': invoice.partner_id.id,
                        'service_type_id': request.service_type_id.id,
                        'payment_date': payment.date,
                        'journal_id': payment.journal_id.id,
                        'amount': payment.amount,
                        'payment_state': invoice.payment_state,
                        'company_id': invoice.company_id.id,
                        'currency_id': payment.currency_id.id or invoice.currency_id.id or currency.id,
                    }))

        receipt_summary_commands = [
            (0, 0, {
                'journal_id': values['journal_id'],
                'amount': values['amount'],
                'payment_count': values['payment_count'],
                'currency_id': currency.id,
            })
            for values in summary_by_journal.values()
        ]

        invoice_line_commands = []
        for invoice in pending_invoices:
            request = invoice.membership_service_request_id
            invoice_line_commands.append((0, 0, {
                'invoice_id': invoice.id,
                'service_request_id': request.id,
                'partner_id': invoice.partner_id.id,
                'service_type_id': request.service_type_id.id,
                'invoice_date': invoice.invoice_date,
                'amount_total': invoice.amount_total,
                'amount_residual': invoice.amount_residual,
                'payment_state': invoice.payment_state,
                'company_id': invoice.company_id.id,
                'currency_id': invoice.currency_id.id or currency.id,
            }))

        return {
            'currency_id': currency.id,
            'allowed_cash_journal_ids': [(6, 0, journals.ids)],
            'allowed_cash_journal_count': len(journals),
            'has_cash_journals': bool(journals),
            'has_pending_invoices': bool(invoice_line_commands),
            'today_receipts': total_receipts,
            'today_paid_invoice_count': len(paid_invoice_ids),
            'pending_residual_total': pending_residual_total,
            'receipt_summary_line_ids': receipt_summary_commands,
            'invoice_line_ids': invoice_line_commands,
            'paid_invoice_line_ids': paid_invoice_line_commands,
        }


class MembershipCashierReceiptSummaryLine(models.TransientModel):
    _name = 'membership.cashier.receipt.summary.line'
    _description = 'حصيلة قبض حسب دفتر اليومية'

    dashboard_id = fields.Many2one('membership.cashier.dashboard', required=True, ondelete='cascade')
    journal_id = fields.Many2one('account.journal', string='دفتر اليومية النقدية', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    amount = fields.Monetary(string='المقبوضات', currency_field='currency_id', readonly=True)
    payment_count = fields.Integer(string='عدد عمليات القبض', readonly=True)


class MembershipCashierInvoiceLine(models.TransientModel):
    _name = 'membership.cashier.invoice.line'
    _description = 'فاتورة خدمة طبيب بانتظار القبض'

    dashboard_id = fields.Many2one('membership.cashier.dashboard', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='رقم الفاتورة', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='رقم طلب الخدمة', readonly=True)
    partner_id = fields.Many2one('res.partner', string='الطبيب', readonly=True)
    service_type_id = fields.Many2one('membership.service.type', string='نوع الخدمة', readonly=True)
    invoice_date = fields.Date(string='تاريخ الفاتورة', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    amount_total = fields.Monetary(string='المبلغ', currency_field='currency_id', readonly=True)
    amount_residual = fields.Monetary(string='المتبقي', currency_field='currency_id', readonly=True)
    payment_state = fields.Selection(related='invoice_id.payment_state', string='حالة الدفع', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

    def action_open_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('الفاتورة'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_register_payment(self):
        self.ensure_one()
        journals = self.env.user.allowed_cash_journal_ids.filtered(
            lambda journal: journal.type == 'cash' and journal.company_id == self.invoice_id.company_id
        )
        if not journals:
            raise UserError(_('لا توجد دفاتر يومية نقدية مسموحة لهذا المستخدم ضمن شركة الفاتورة.'))
        action = self.invoice_id.action_register_payment()
        context = dict(action.get('context') or {})
        context.update({
            'membership_service_cashier_payment': True,
            'allowed_cash_journal_ids': journals.ids,
            'default_journal_id': journals[0].id,
            'cashier_dashboard_date_filter': self.dashboard_id.date_filter,
            'cashier_dashboard_date_from': fields.Date.to_string(self.dashboard_id.date_from),
            'cashier_dashboard_date_to': fields.Date.to_string(self.dashboard_id.date_to),
        })
        action['context'] = context
        return action


class MembershipCashierPaidInvoiceLine(models.TransientModel):
    _name = 'membership.cashier.paid.invoice.line'
    _description = 'فاتورة خدمة طبيب مقبوضة'

    dashboard_id = fields.Many2one('membership.cashier.dashboard', required=True, ondelete='cascade')
    payment_id = fields.Many2one('account.payment', string='عملية القبض', readonly=True)
    invoice_id = fields.Many2one('account.move', string='رقم الفاتورة', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='رقم طلب الخدمة', readonly=True)
    partner_id = fields.Many2one('res.partner', string='الطبيب', readonly=True)
    service_type_id = fields.Many2one('membership.service.type', string='نوع الخدمة', readonly=True)
    payment_date = fields.Date(string='تاريخ القبض', readonly=True)
    journal_id = fields.Many2one('account.journal', string='دفتر اليومية النقدية', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    amount = fields.Monetary(string='المبلغ المقبوض', currency_field='currency_id', readonly=True)
    payment_state = fields.Selection(related='invoice_id.payment_state', string='حالة الدفع', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

    def action_open_invoice(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('الفاتورة'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_payment_for_reversal(self):
        self.ensure_one()
        if not (
            self.env.user.has_group('membership_management.group_membership_service_manager')
            or self.env.user.has_group('account.group_account_manager')
        ):
            raise UserError(_('لا تملك صلاحية استرجاع المبلغ أو إلغاء عملية القبض.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('استرجاع أو إلغاء عملية القبض'),
            'res_model': 'account.payment',
            'res_id': self.payment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
