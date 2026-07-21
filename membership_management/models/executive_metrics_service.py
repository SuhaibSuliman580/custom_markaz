from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class ExecutiveMetricsService(models.AbstractModel):
    _name = 'membership.executive.metrics.service'
    _description = 'خدمة مؤشرات الذكاء التنفيذي'
    _inherit = 'membership.workspace.mixin'

    @api.model
    def _allowed_company_ids(self, company_id=False):
        allowed = set(self.env.companies.ids)
        if company_id:
            if company_id not in allowed:
                raise AccessError(_('الشركة المحددة ليست ضمن الشركات المسموحة للمستخدم.'))
            return [company_id]
        return sorted(allowed)

    @api.model
    def _is_invoice_overdue(self, invoice, reference_date):
        return bool(
            invoice.invoice_date_due
            and invoice.invoice_date_due < reference_date
            and invoice.state == 'posted'
            and invoice.payment_state not in ('paid', 'reversed')
        )

    @api.model
    def _is_draft_move_aged(self, move, reference_date, age_days=7):
        return bool(
            move.state == 'draft' and move.date
            and move.date < reference_date - timedelta(days=age_days)
        )

    @api.model
    def _get_executive_metrics(self, company_id=False, date_from=False, date_to=False):
        """Reuse V2 as the single aggregation layer for one refresh operation."""
        company_ids = self._allowed_company_ids(company_id)
        dates = self.env['membership.command.center']._default_dates()
        center = self.env['membership.command.center'].create({
            'company_id': company_id or False,
            'date_from': date_from or dates[0],
            'date_to': date_to or dates[1],
        })
        center._refresh_values()
        scalar_fields = [
            'doctor_total', 'doctor_complete_count', 'doctor_incomplete_count',
            'doctor_missing_national_id', 'doctor_missing_specialty',
            'doctor_duplicate_national_id', 'doctor_unassigned_count',
            'doctor_completion_rate', 'doctor_missing_national_rate',
            'doctor_missing_specialty_rate', 'doctor_duplicate_rate',
            'new_application_count', 'renewal_count', 'request_processing_count',
            'request_delayed_count', 'request_created_period_count',
            'request_completed_period_count', 'completed_today_count',
            'revenue_today', 'receipts_today', 'unpaid_invoice_total',
            'overdue_amount', 'draft_move_count', 'posted_waiting_payment_count',
            'distributed_revenue_total', 'distribution_issue_count',
            'open_task_count', 'due_today_task_count', 'overdue_task_count',
            'unassigned_request_count', 'collection_rate', 'health_score',
            'evaluation_confidence',
        ]
        result = {name: center[name] for name in scalar_fields}
        result.update({
            'company_ids': company_ids,
            'company_id': company_id or False,
            'currency_id': center.currency_id.id,
            'date_from': center.date_from,
            'date_to': center.date_to,
            'branch_lines': center.branch_line_ids.read([
                'company_id', 'doctor_count', 'open_request_count',
                'delayed_request_count', 'branch_health_score',
                'has_health_score', 'evaluation_confidence',
            ]),
            'employee_lines': center.employee_line_ids.read([
                'user_id', 'assigned_count', 'delayed_count',
                'overdue_task_count',
            ]),
            'event_lines': center.event_line_ids.read([
                'event_date', 'event_type', 'description', 'company_id',
                'user_id', 'res_model', 'res_id',
            ]),
        })
        today = fields.Date.context_today(self)
        start_utc, stop_utc = self._workspace_today_bounds_utc()
        company_domain = [('company_id', 'in', company_ids)]
        invoice_domain = company_domain + [
            ('move_type', '=', 'out_invoice'),
            ('membership_service_request_id', '!=', False),
        ]
        invoices_today = self.env['account.move'].search(
            invoice_domain + [('create_date', '>=', start_utc), ('create_date', '<', stop_utc)])
        overdue_invoices = self.env['account.move'].search(
            invoice_domain + [('state', '=', 'posted'), ('payment_state', 'not in', ('paid', 'reversed')),
                              ('invoice_date_due', '<', today)])
        open_request_count = self.env['membership.service.request'].search_count(
            company_domain + [('state', 'not in', ('completed', 'cancelled'))])
        draft_age_days = 7
        aged_draft_domain = company_domain + [
            ('state', '=', 'draft'), ('date', '<', today - timedelta(days=draft_age_days)),
        ]
        result.update({
            'invoice_today_count': len(invoices_today),
            'invoice_today_amount': sum(invoices_today.mapped('amount_total')),
            'overdue_invoice_count': len(overdue_invoices),
            'overdue_invoice_amount': sum(overdue_invoices.mapped('amount_residual')),
            'open_request_count': open_request_count,
            'delayed_request_rate': (
                self.env['membership.command.center']._bounded_percentage(
                    result['request_delayed_count'], open_request_count)
                if open_request_count else False
            ),
            'aged_draft_move_count': self.env['account.move'].search_count(aged_draft_domain),
            'draft_move_age_days': draft_age_days,
            'new_doctor_count': self.env['res.partner'].search_count(
                company_domain + [('is_doctor', '=', True),
                                  ('create_date', '>=', start_utc), ('create_date', '<', stop_utc)]),
        })
        return result

    @api.model
    def _open_domain(self, model, name, domain):
        safe_domain = list(domain or [])
        if model in self.env.registry.models and 'company_id' in self.env[model]._fields:
            safe_domain = [('company_id', 'in', self._allowed_company_ids())] + safe_domain
        return {
            'type': 'ir.actions.act_window', 'name': name, 'res_model': model,
            'view_mode': 'tree,form', 'domain': safe_domain, 'target': 'current',
        }
