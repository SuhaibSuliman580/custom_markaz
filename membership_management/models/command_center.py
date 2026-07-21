from collections import defaultdict
from datetime import timedelta
import logging
import time

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


class MembershipCommandCenter(models.TransientModel):
    _name = 'membership.command.center'
    _description = 'مركز القيادة والإدارة'
    _inherit = 'membership.workspace.mixin'
    _rec_name = 'name'

    HEALTHY_MIN = 85.0
    FOLLOW_UP_MIN = 70.0
    IMPORTANT_MIN = 50.0

    name = fields.Char(default='مركز القيادة والإدارة', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='النقابة الفرعية',
        domain=lambda self: [('id', 'in', self.env.companies.ids)],
    )
    allowed_company_ids = fields.Many2many(
        'res.company', string='النقابات المسموحة', compute='_compute_allowed_companies',
    )
    date_from = fields.Date(string='من تاريخ')
    date_to = fields.Date(string='إلى تاريخ', default=fields.Date.context_today)
    service_type_id = fields.Many2one('membership.service.type', string='نوع المعاملة')
    request_state = fields.Selection([
        ('draft', 'مسودة'),
        ('waiting_financial_approval', 'بانتظار تصديق المالية'),
        ('waiting_payment', 'بانتظار الدفع'),
        ('paid', 'مدفوع'),
        ('in_progress', 'قيد التنفيذ'),
        ('completed', 'منجز'),
        ('cancelled', 'ملغى'),
    ], string='حالة المعاملة')
    responsible_user_id = fields.Many2one('res.users', string='الموظف المسؤول')
    currency_id = fields.Many2one('res.currency', readonly=True)
    is_central_view = fields.Boolean(string='عرض مركزي', readonly=True)
    display_title = fields.Char(string='العنوان التنفيذي', readonly=True)
    overall_status = fields.Selection([
        ('normal', 'يعمل بشكل طبيعي'),
        ('follow_up', 'يحتاج متابعة'),
        ('important', 'توجد مشكلات مهمة'),
        ('critical', 'توجد مشكلات حرجة'),
        ('insufficient', 'بيانات غير كافية'),
    ], string='الحالة العامة', readonly=True)
    overall_status_label = fields.Char(string='وصف الحالة', readonly=True)
    overall_status_message = fields.Char(string='الرسالة التنفيذية', readonly=True)
    health_score = fields.Float(string='درجة الصحة', readonly=True)
    data_quality_score = fields.Float(string='جودة البيانات', readonly=True)
    transaction_score = fields.Float(string='المعاملات', readonly=True)
    financial_score = fields.Float(string='المالية', readonly=True)
    task_score = fields.Float(string='المهام', readonly=True)
    alert_score = fields.Float(string='التنبيهات', readonly=True)
    evaluation_confidence = fields.Selection([
        ('high', 'مرتفعة'), ('medium', 'متوسطة'), ('low', 'منخفضة'),
    ], string='ثقة التقييم', readonly=True)
    evaluation_confidence_label = fields.Char(string='ثقة التقييم', readonly=True)
    critical_alert_count = fields.Integer(string='مؤشرات حرجة', readonly=True)
    warning_alert_count = fields.Integer(string='مؤشرات تحتاج متابعة', readonly=True)
    normal_indicator_count = fields.Integer(string='مؤشرات طبيعية', readonly=True)

    doctor_total = fields.Integer(string='إجمالي الأطباء', readonly=True)
    doctor_complete_count = fields.Integer(string='الملفات المكتملة', readonly=True)
    doctor_incomplete_count = fields.Integer(string='الملفات الناقصة', readonly=True)
    doctor_missing_national_id = fields.Integer(string='بدون رقم وطني', readonly=True)
    doctor_missing_specialty = fields.Integer(string='بدون اختصاص', readonly=True)
    doctor_missing_phone = fields.Integer(string='بدون هاتف', readonly=True)
    doctor_duplicate_national_id = fields.Integer(string='أرقام وطنية مكررة', readonly=True)
    doctor_unassigned_count = fields.Integer(
        string='أطباء غير مرتبطين بنقابة فرعية', readonly=True,
    )
    doctor_completion_rate = fields.Float(string='نسبة اكتمال البيانات', readonly=True)
    doctor_incomplete_rate = fields.Float(string='نسبة الملفات الناقصة', readonly=True)
    doctor_missing_national_rate = fields.Float(string='نسبة بدون رقم وطني', readonly=True)
    doctor_missing_specialty_rate = fields.Float(string='نسبة بدون اختصاص', readonly=True)
    doctor_missing_phone_rate = fields.Float(string='نسبة بدون هاتف', readonly=True)
    doctor_duplicate_rate = fields.Float(string='نسبة التكرار', readonly=True)

    new_application_count = fields.Integer(string='طلبات الانتساب الجديدة', readonly=True)
    renewal_count = fields.Integer(string='طلبات التجديد', readonly=True)
    profile_update_count = fields.Integer(string='طلبات تعديل البيانات', readonly=True)
    request_processing_count = fields.Integer(string='قيد المعالجة', readonly=True)
    request_delayed_count = fields.Integer(string='المعاملات المتأخرة', readonly=True)
    request_rejected_count = fields.Integer(string='المعادة أو المرفوضة', readonly=True)
    request_created_period_count = fields.Integer(string='طلبات منشأة خلال الفترة', readonly=True)
    request_completed_period_count = fields.Integer(string='طلبات منجزة خلال الفترة', readonly=True)

    revenue_today = fields.Monetary(string='إيرادات اليوم', currency_field='currency_id', readonly=True)
    revenue_month = fields.Monetary(string='إيرادات الشهر', currency_field='currency_id', readonly=True)
    receipts_today = fields.Monetary(string='المقبوضات اليوم', currency_field='currency_id', readonly=True)
    receipts_month = fields.Monetary(string='المقبوضات الشهرية', currency_field='currency_id', readonly=True)
    unpaid_invoice_total = fields.Monetary(string='الفواتير غير المحصلة', currency_field='currency_id', readonly=True)
    unpaid_period_amount = fields.Monetary(
        string='غير المحصل من فواتير الفترة', currency_field='currency_id', readonly=True,
    )
    total_outstanding_amount = fields.Monetary(
        string='إجمالي الرصيد غير المحصل حتى نهاية الفترة', currency_field='currency_id', readonly=True,
    )
    overdue_amount = fields.Monetary(
        string='المبلغ المتجاوز لتاريخ الاستحقاق', currency_field='currency_id', readonly=True,
    )
    draft_move_count = fields.Integer(string='القيود غير المرحلة', readonly=True)
    posted_waiting_payment_count = fields.Integer(string='فواتير بانتظار الدفع', readonly=True)

    active_fund_count = fields.Integer(string='الصناديق الفعالة', readonly=True)
    distributed_revenue_total = fields.Monetary(string='الإيرادات الموزعة', currency_field='currency_id', readonly=True)
    distribution_issue_count = fields.Integer(string='مشكلات التوزيع', readonly=True)
    open_task_count = fields.Integer(string='المهام المفتوحة', readonly=True)
    due_today_task_count = fields.Integer(string='المهام المستحقة اليوم', readonly=True)
    overdue_task_count = fields.Integer(string='المهام المتأخرة', readonly=True)
    unassigned_request_count = fields.Integer(string='المعاملات غير المسندة', readonly=True)
    completed_today_count = fields.Integer(string='المعاملات المنجزة اليوم', readonly=True)
    average_completion_hours = fields.Float(string='متوسط زمن الإنجاز (ساعة)', readonly=True)
    average_completion_label = fields.Char(string='متوسط زمن الإنجاز', readonly=True)
    has_average_completion = fields.Boolean(string='يتوفر متوسط زمن الإنجاز', readonly=True)
    period_label = fields.Char(string='الفترة الحالية', readonly=True)
    has_employee_data = fields.Boolean(string='تتوفر بيانات أداء الموظفين', readonly=True)
    collection_rate = fields.Float(string='نسبة التحصيل', readonly=True)
    fund_month_revenue = fields.Monetary(string='توزيعات الصناديق هذا الشهر', currency_field='currency_id', readonly=True)
    top_fund_name = fields.Char(string='أعلى صندوق إيرادًا', readonly=True)
    fund_without_movement_count = fields.Integer(string='صناديق بدون حركة', readonly=True)

    branch_line_ids = fields.One2many('membership.command.center.branch.line', 'center_id', readonly=True)
    fund_line_ids = fields.One2many('membership.command.center.fund.line', 'center_id', readonly=True)
    alert_line_ids = fields.One2many('membership.command.center.alert.line', 'center_id', readonly=True)
    employee_line_ids = fields.One2many('membership.command.center.employee.line', 'center_id', readonly=True)
    event_line_ids = fields.One2many('membership.command.center.event.line', 'center_id', readonly=True)

    @api.model
    def _bounded_percentage(self, numerator, denominator):
        if not denominator:
            return 0.0
        return max(0.0, min(100.0, (numerator / denominator) * 100.0))

    @api.model
    def _get_data_quality_score(self, completion_rate):
        return max(0.0, min(30.0, completion_rate * 0.30))

    @api.model
    def _get_transaction_score(self, total_open, delayed):
        return 0.0 if not total_open else max(0.0, 25.0 * (1.0 - delayed / total_open))

    @api.model
    def _get_financial_score(self, invoiced, collected, draft_moves, distribution_issues):
        collection = 0.0 if not invoiced else min(1.0, max(0.0, collected / invoiced))
        penalty = min(5.0, draft_moves * 0.25 + distribution_issues)
        return max(0.0, 20.0 * collection - penalty)

    @api.model
    def _get_task_score(self, open_tasks, overdue_tasks):
        return 0.0 if not open_tasks else max(0.0, 15.0 * (1.0 - overdue_tasks / open_tasks))

    @api.model
    def _get_alert_score(self, critical_count):
        return max(0.0, 10.0 - critical_count * 2.0)

    @api.model
    def _compute_health_score(self, completion_rate, open_requests, delayed_requests,
                              invoiced, collected, draft_moves, distribution_issues,
                              open_tasks, overdue_tasks, critical_count):
        return self._health_score_details(
            completion_rate, open_requests, delayed_requests, invoiced, collected,
            draft_moves, distribution_issues, open_tasks, overdue_tasks, critical_count,
            has_data_quality=True, has_transactions=bool(open_requests),
            has_financial=bool(invoiced), has_tasks=bool(open_tasks), has_alerts=True,
        )['health_score']

    @api.model
    def _health_score_details(self, completion_rate, open_requests, delayed_requests,
                              invoiced, collected, draft_moves, distribution_issues,
                              open_tasks, overdue_tasks, critical_count, *,
                              has_data_quality, has_transactions, has_financial,
                              has_tasks, has_alerts):
        components = {
            'data_quality_score': self._get_data_quality_score(completion_rate),
            'transaction_score': self._get_transaction_score(open_requests, delayed_requests),
            'financial_score': self._get_financial_score(
                invoiced, collected, draft_moves, distribution_issues,
            ),
            'task_score': self._get_task_score(open_tasks, overdue_tasks),
            'alert_score': self._get_alert_score(critical_count),
        }
        measurable = (
            ('data_quality_score', 30.0, has_data_quality),
            ('transaction_score', 25.0, has_transactions),
            ('financial_score', 20.0, has_financial),
            ('task_score', 15.0, has_tasks),
            ('alert_score', 10.0, has_alerts),
        )
        available = [(components[key], maximum) for key, maximum, enabled in measurable if enabled]
        score = self._bounded_percentage(
            sum(value for value, _maximum in available),
            sum(maximum for _value, maximum in available),
        ) if available else False
        measured_axes = len(available)
        confidence = 'high' if measured_axes >= 4 else ('medium' if measured_axes == 3 else 'low')
        labels = {'high': _('مرتفعة'), 'medium': _('متوسطة'), 'low': _('منخفضة')}
        return {
            **components,
            'health_score': score,
            'evaluation_confidence': confidence,
            'evaluation_confidence_label': labels[confidence],
        }

    @api.model
    def _financial_amounts(self, period_invoices, outstanding_invoices, reference_date):
        unpaid_period = sum(
            max(0.0, invoice.amount_residual) for invoice in period_invoices
        )
        total_outstanding = sum(
            max(0.0, invoice.amount_residual) for invoice in outstanding_invoices
        )
        overdue = sum(
            max(0.0, invoice.amount_residual)
            for invoice in outstanding_invoices
            if invoice.invoice_date_due and invoice.invoice_date_due < reference_date
        )
        return unpaid_period, total_outstanding, overdue

    @api.model
    def _overall_status_values(self, score, has_data):
        if not has_data:
            return 'insufficient', _('بيانات غير كافية'), _('لا تتوفر بيانات أساسية كافية لإصدار تقييم تنفيذي.')
        if score >= self.HEALTHY_MIN:
            return 'normal', _('يعمل بشكل طبيعي'), _('الوضع العام مستقر ولا توجد مؤشرات تستدعي تدخلاً عاجلاً.')
        if score >= self.FOLLOW_UP_MIN:
            return 'follow_up', _('يحتاج متابعة'), _('الأداء مقبول مع مؤشرات تتطلب متابعة وتحسينًا.')
        if score >= self.IMPORTANT_MIN:
            return 'important', _('توجد مشكلات مهمة'), _('توجد مشكلات مؤثرة تستدعي خطة معالجة قريبة.')
        return 'critical', _('توجد مشكلات حرجة'), _('الأولوية لمعالجة التأخيرات والتحصيل وجودة البيانات.')

    @api.depends_context('allowed_company_ids')
    def _compute_allowed_companies(self):
        for rec in self:
            rec.allowed_company_ids = self.env.companies

    @api.model
    def _doctor_required_fields(self):
        return ('name', 'national_id', 'medical_specialty_id', 'phone_or_mobile', 'company_id')

    @api.model
    def _doctor_scope_domain(self, company_ids, include_unassigned=False):
        domain = [('is_doctor', '=', True)]
        if include_unassigned:
            domain += ['|', ('company_id', '=', False), ('company_id', 'in', company_ids)]
        else:
            domain.append(('company_id', 'in', company_ids))
        return domain

    @api.model
    def _doctor_branch_domain(self, company_id):
        return [('is_doctor', '=', True), ('company_id', '=', company_id)]

    @api.model
    def _doctor_unassigned_domain(self):
        return [('is_doctor', '=', True), ('company_id', '=', False)]

    @api.model
    def _doctor_quality_domains(self, company_ids, include_unassigned=False):
        base = self._doctor_scope_domain(company_ids, include_unassigned=include_unassigned)
        missing = [
            '|', '|', '|', '|',
            ('name', '=', False),
            ('national_id', '=', False),
            ('medical_specialty_id', '=', False),
            '&', ('phone', '=', False), ('mobile', '=', False),
            ('company_id', '=', False),
        ]
        return {
            'base': base,
            'complete': base + ['!'] + missing,
            'incomplete': base + missing,
            'missing_national': base + [('national_id', '=', False)],
            'missing_specialty': base + [('medical_specialty_id', '=', False)],
            'missing_phone': base + [('phone', '=', False), ('mobile', '=', False)],
        }

    @api.model
    def _format_duration(self, hours):
        if hours < 1:
            return _('%s دقيقة') % round(hours * 60)
        if hours < 24:
            return _('%s ساعة') % round(hours, 1)
        return _('%s يوم') % round(hours / 24.0, 1)

    @api.model
    def _doctor_counts_reconcile(self, total_count, branch_count, unassigned_count):
        return total_count == branch_count + unassigned_count

    @api.model
    def _collection_amounts(self, invoices):
        due_amount = sum(max(0.0, invoice.amount_total) for invoice in invoices)
        collected_amount = sum(
            max(0.0, invoice.amount_total - invoice.amount_residual)
            for invoice in invoices
        )
        collected_amount = min(due_amount, collected_amount)
        return due_amount, collected_amount, self._bounded_percentage(
            collected_amount, due_amount,
        )

    @api.model
    def _valid_completion_hours(self, requests):
        durations = []
        for request in requests:
            if not request.started_date or not request.completed_date:
                continue
            if request.completed_date < request.started_date:
                continue
            durations.append(
                (request.completed_date - request.started_date).total_seconds() / 3600.0
            )
        return durations

    @api.model
    def _allowed_company_ids(self, requested_company=False):
        allowed = self.env.companies.ids
        if requested_company:
            if requested_company.id not in allowed:
                raise AccessError(_('لا تملك صلاحية الوصول إلى هذه النقابة الفرعية.'))
            return [requested_company.id]
        return allowed

    @api.model
    def _default_dates(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1), today

    @api.model
    def action_open_command_center(self):
        date_from, date_to = self._default_dates()
        vals = {
            'date_from': date_from,
            'date_to': date_to,
            'company_id': self.env.company.id if len(self.env.companies) == 1 else False,
        }
        center = self.create(vals)
        center._refresh_values()
        return {
            'type': 'ir.actions.act_window',
            'name': _('مركز القيادة والإدارة'),
            'res_model': self._name,
            'res_id': center.id,
            'view_mode': 'form',
            'view_id': self.env.ref('membership_management.view_membership_command_center_form').id,
            'target': 'current',
        }

    def action_refresh(self):
        self.ensure_one()
        self._refresh_values()
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_decision_center(self):
        return self.env['membership.decision.center'].action_open_center()

    def action_open_daily_brief(self):
        return self.env['membership.daily.brief'].action_open_brief()

    def action_open_risk_center(self):
        return self.env['membership.risk.center'].action_open_center()

    def action_open_executive_timeline(self):
        return self.env['membership.executive.timeline'].action_open_timeline()

    def action_reset_filters(self):
        self.ensure_one()
        date_from, date_to = self._default_dates()
        self.write({
            'company_id': self.env.company.id if len(self.env.companies) == 1 else False,
            'date_from': date_from, 'date_to': date_to,
            'service_type_id': False, 'request_state': False, 'responsible_user_id': False,
        })
        return self.action_refresh()

    def _set_quick_period(self, date_from, date_to):
        self.ensure_one()
        self.write({'date_from': date_from, 'date_to': date_to})
        return self.action_refresh()

    def action_period_today(self):
        today = fields.Date.context_today(self)
        return self._set_quick_period(today, today)

    def action_period_week(self):
        today = fields.Date.context_today(self)
        return self._set_quick_period(today - timedelta(days=today.weekday()), today)

    def action_period_month(self):
        today = fields.Date.context_today(self)
        return self._set_quick_period(today.replace(day=1), today)

    def action_period_year(self):
        today = fields.Date.context_today(self)
        return self._set_quick_period(today.replace(month=1, day=1), today)

    def _date_domain(self, field_name):
        domain = []
        if self.date_from:
            domain.append((field_name, '>=', self.date_from))
        if self.date_to:
            domain.append((field_name, '<=', self.date_to))
        return domain

    def _datetime_domain(self, field_name):
        domain = []
        if self.date_from:
            domain.append((field_name, '>=', fields.Datetime.to_datetime(self.date_from)))
        if self.date_to:
            stop = fields.Datetime.to_datetime(self.date_to + timedelta(days=1))
            domain.append((field_name, '<', stop))
        return domain

    def _service_request_base_domain(self, company_ids):
        domain = [('company_id', 'in', company_ids)]
        if self.service_type_id:
            domain.append(('service_type_id', '=', self.service_type_id.id))
        if self.request_state:
            domain.append(('state', '=', self.request_state))
        if self.responsible_user_id:
            domain += ['|', '|',
                ('submitted_by_id', '=', self.responsible_user_id.id),
                ('started_by_id', '=', self.responsible_user_id.id),
                ('completed_by_id', '=', self.responsible_user_id.id),
            ]
        return domain

    def _refresh_values(self):
        self.ensure_one()
        started_at = time.monotonic()
        company_ids = self._allowed_company_ids(self.company_id)
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)
        currency = (self.company_id or self.env.company).currency_id
        Partner = self.env['res.partner']
        Request = self.env['membership.service.request']
        Application = self.env['membership.application']
        Profile = self.env['membership.profile.update']
        Period = self.env['membership.period']
        Move = self.env['account.move']
        Payment = self.env['account.payment']
        Activity = self.env['mail.activity']
        Fund = self.env['syndicate.fund.box']
        Ledger = self.env['syndicate.revenue.distribution.ledger.line']

        include_unassigned_doctors = not bool(self.company_id)
        quality = self._doctor_quality_domains(
            company_ids, include_unassigned=include_unassigned_doctors,
        )
        doctors = Partner.search(quality['base'])
        assigned_doctors = doctors.filtered(lambda doctor: doctor.company_id.id in company_ids)
        unassigned_doctors = doctors - assigned_doctors
        complete = doctors.filtered(
            lambda d: d.name and d.national_id and d.medical_specialty_id
            and (d.phone or d.mobile) and d.company_id
        )
        national_counts = defaultdict(int)
        for doctor in doctors.filtered('national_id'):
            national_counts[doctor.national_id.strip()] += 1
        duplicate_count = sum(count for count in national_counts.values() if count > 1)

        request_domain = self._service_request_base_domain(company_ids)
        requests = Request.search(request_domain + self._datetime_domain('create_date'))
        open_requests = Request.search(
            request_domain + [('state', 'not in', ('completed', 'cancelled'))]
        )
        delay_cutoff = fields.Datetime.now() - timedelta(days=7)
        delayed_requests = open_requests.filtered(lambda r: r.create_date and r.create_date < delay_cutoff)
        completed_period = Request.search(
            request_domain + [('state', '=', 'completed')]
            + self._datetime_domain('completed_date')
        )
        completed_today = completed_period.filtered(
            lambda r: r.completed_date and fields.Date.to_date(r.completed_date) == today
        )
        valid_completion_hours = self._valid_completion_hours(completed_period)
        average_hours = (
            sum(valid_completion_hours) / len(valid_completion_hours)
        ) if valid_completion_hours else 0.0

        invoice_base = [
            ('company_id', 'in', company_ids),
            ('move_type', '=', 'out_invoice'),
            ('membership_service_request_id', '!=', False),
        ]
        posted_invoices = Move.search(
            invoice_base + [('state', '=', 'posted')] + self._date_domain('invoice_date')
        )
        reference_date = min(self.date_to or today, today)
        outstanding_invoices = Move.search(invoice_base + [
            ('state', '=', 'posted'),
            ('amount_residual', '>', 0),
            ('invoice_date', '<=', reference_date),
        ])
        payments = Payment.search([
            ('company_id', 'in', company_ids), ('state', '=', 'posted'),
            ('payment_type', '=', 'inbound'),
        ] + self._date_domain('date'))
        activities = Activity.search([
            ('res_model', '=', 'membership.service.request'),
            ('res_id', 'in', (requests | open_requests | completed_period).ids or [0]),
        ])
        funds = Fund.search([('company_id', 'in', company_ids), ('active', '=', True)])
        ledger = Ledger.search([
            ('company_id', 'in', company_ids), ('state', '=', 'posted'),
        ] + self._date_domain('invoice_date'))

        applications = Application.search(
            [('company_id', 'in', company_ids)] + self._datetime_domain('create_date')
        )
        profiles = Profile.search(
            [('company_id', 'in', company_ids)] + self._datetime_domain('create_date')
        )
        renewals = Period.search(
            [('company_id', 'in', company_ids), ('period_type', '=', 'renewal')]
            + self._date_domain('start_date')
        )
        total_doctors = len(doctors)
        completion_rate = self._bounded_percentage(len(complete), total_doctors)
        due_amount, collected_total, collection_rate = self._collection_amounts(posted_invoices)
        unpaid_period_amount, total_outstanding_amount, overdue_amount = self._financial_amounts(
            posted_invoices.filtered(lambda move: move.amount_residual > 0),
            outstanding_invoices,
            reference_date,
        )
        overdue_activities = activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)
        distribution_issues = len(requests.filtered(
            lambda r: r.revenue_distribution_required and not r.revenue_distribution_ready
        ))
        draft_move_count = Move.search_count([
            ('company_id', 'in', company_ids), ('state', '=', 'draft'),
        ])
        branch_doctor_total = sum(
            len(assigned_doctors.filtered(lambda doctor: doctor.company_id.id == company_id))
            for company_id in company_ids
        )
        distribution_matches = self._doctor_counts_reconcile(
            total_doctors, branch_doctor_total, len(unassigned_doctors),
        )
        alert_commands = self._prepare_alert_lines(
            delayed_requests, posted_invoices, activities, doctors=doctors,
            draft_move_count=draft_move_count,
            distribution_issue_count=distribution_issues,
            outstanding_invoices=outstanding_invoices,
            reference_date=reference_date,
            doctor_distribution_matches=distribution_matches,
        )
        alert_values = [command[2] for command in alert_commands if command[0] == 0]
        critical_count = sum(1 for row in alert_values if row.get('severity') == 'critical')
        warning_count = sum(1 for row in alert_values if row.get('severity') == 'warning')
        health_details = self._health_score_details(
            completion_rate, len(open_requests), len(delayed_requests),
            due_amount, collected_total,
            draft_move_count,
            distribution_issues, len(activities), len(overdue_activities), critical_count,
            has_data_quality=bool(doctors),
            has_transactions=bool(requests or open_requests or completed_period),
            has_financial=bool(posted_invoices or payments),
            has_tasks=bool(activities),
            has_alerts=bool(doctors or requests or open_requests or posted_invoices or payments or activities),
        )
        health_score = health_details['health_score'] or 0.0
        status, status_label, status_message = self._overall_status_values(
            health_score, bool(doctors or requests or open_requests or posted_invoices or payments)
        )
        fund_totals = {
            fund.id: sum(ledger.filtered(lambda row: row.fund_box_id == fund).mapped('distributed_amount'))
            for fund in funds
        }
        top_fund = max(funds, key=lambda fund: fund_totals.get(fund.id, 0.0), default=False)
        month_ledger = ledger.filtered(lambda row: row.invoice_date and month_start <= row.invoice_date <= today)
        incomplete_count = len(doctors - complete)
        missing_national_count = len(doctors.filtered(lambda d: not d.national_id))
        missing_specialty_count = len(doctors.filtered(lambda d: not d.medical_specialty_id))
        missing_phone_count = len(doctors.filtered(lambda d: not d.phone and not d.mobile))
        incomplete_rate = self._bounded_percentage(incomplete_count, total_doctors)
        missing_national_rate = self._bounded_percentage(missing_national_count, total_doctors)
        missing_specialty_rate = self._bounded_percentage(missing_specialty_count, total_doctors)
        missing_phone_rate = self._bounded_percentage(missing_phone_count, total_doctors)
        duplicate_rate = self._bounded_percentage(duplicate_count, total_doctors)
        values = {
            'currency_id': currency.id,
            'display_title': _('مركز إدارة %s') % self.company_id.display_name if self.company_id else _('مركز القيادة التنفيذي'),
            'is_central_view': len(company_ids) > 1 and not self.company_id,
            'overall_status': status,
            'overall_status_label': status_label,
            'overall_status_message': status_message,
            'health_score': health_score,
            'data_quality_score': health_details['data_quality_score'],
            'transaction_score': health_details['transaction_score'],
            'financial_score': health_details['financial_score'],
            'task_score': health_details['task_score'],
            'alert_score': health_details['alert_score'],
            'evaluation_confidence': health_details['evaluation_confidence'],
            'evaluation_confidence_label': health_details['evaluation_confidence_label'],
            'critical_alert_count': critical_count,
            'warning_alert_count': warning_count,
            'normal_indicator_count': max(0, 10 - critical_count - warning_count),
            'doctor_total': total_doctors,
            'doctor_complete_count': len(complete),
            'doctor_incomplete_count': incomplete_count,
            'doctor_missing_national_id': missing_national_count,
            'doctor_missing_specialty': missing_specialty_count,
            'doctor_missing_phone': missing_phone_count,
            'doctor_duplicate_national_id': duplicate_count,
            'doctor_unassigned_count': len(unassigned_doctors),
            'doctor_completion_rate': completion_rate,
            'doctor_incomplete_rate': incomplete_rate,
            'doctor_missing_national_rate': missing_national_rate,
            'doctor_missing_specialty_rate': missing_specialty_rate,
            'doctor_missing_phone_rate': missing_phone_rate,
            'doctor_duplicate_rate': duplicate_rate,
            'new_application_count': len(applications.filtered(lambda a: a.state in ('draft', 'need_info'))),
            'renewal_count': len(renewals),
            'profile_update_count': len(profiles.filtered(lambda p: p.state in ('draft', 'need_info'))),
            'request_processing_count': len(open_requests),
            'request_delayed_count': len(delayed_requests),
            'request_rejected_count': len(applications.filtered(lambda a: a.state == 'rejected')) + len(profiles.filtered(lambda p: p.state == 'rejected')) + len(requests.filtered(lambda r: r.state == 'cancelled')),
            'request_created_period_count': len(requests),
            'request_completed_period_count': len(completed_period),
            'revenue_today': sum(posted_invoices.filtered(lambda m: m.invoice_date == today).mapped('amount_untaxed_signed')),
            'revenue_month': sum(posted_invoices.mapped('amount_untaxed_signed')),
            'receipts_today': sum(payments.filtered(lambda p: p.date == today).mapped('amount')),
            'receipts_month': sum(payments.mapped('amount')),
            'unpaid_invoice_total': unpaid_period_amount,
            'unpaid_period_amount': unpaid_period_amount,
            'total_outstanding_amount': total_outstanding_amount,
            'overdue_amount': overdue_amount,
            'draft_move_count': draft_move_count,
            'posted_waiting_payment_count': len(posted_invoices.filtered(lambda m: m.payment_state not in ('paid', 'reversed'))),
            'active_fund_count': len(funds),
            'distributed_revenue_total': sum(ledger.mapped('distributed_amount')),
            'distribution_issue_count': len(requests.filtered(lambda r: r.revenue_distribution_required and not r.revenue_distribution_ready)),
            'open_task_count': len(activities),
            'due_today_task_count': len(activities.filtered(lambda a: a.date_deadline == today)),
            'overdue_task_count': len(activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)),
            'unassigned_request_count': len(open_requests.filtered(lambda r: not (r.started_by_id or r.submitted_by_id))),
            'completed_today_count': len(completed_today),
            'average_completion_hours': average_hours,
            'average_completion_label': self._format_duration(average_hours) if valid_completion_hours else _('غير متوفر'),
            'has_average_completion': bool(valid_completion_hours),
            'period_label': _('الفترة: من %(from)s إلى %(to)s') % {
                'from': self.date_from or _('البداية'),
                'to': self.date_to or _('اليوم'),
            },
            'collection_rate': collection_rate,
            'fund_month_revenue': sum(month_ledger.mapped('distributed_amount')),
            'top_fund_name': top_fund.display_name if top_fund and fund_totals.get(top_fund.id) else _('بدون حركة'),
            'fund_without_movement_count': len(funds.filtered(lambda fund: not fund_totals.get(fund.id))),
            'branch_line_ids': [(5, 0, 0)] + self._prepare_branch_lines(company_ids, assigned_doctors, requests, open_requests, posted_invoices, payments, funds, activities, complete & assigned_doctors),
            'fund_line_ids': [(5, 0, 0)] + self._prepare_fund_lines(funds, ledger),
            'alert_line_ids': [(5, 0, 0)] + alert_commands,
            'employee_line_ids': [(5, 0, 0)] + self._prepare_employee_lines(requests | open_requests | completed_period, activities),
            'event_line_ids': [(5, 0, 0)] + self._prepare_event_lines(requests, posted_invoices, payments, ledger),
        }
        values['has_employee_data'] = bool(values['employee_line_ids'][1:])
        if not distribution_matches:
            _logger.warning(
                'Doctor KPI reconciliation failed: total=%s branches=%s unassigned=%s',
                total_doctors, branch_doctor_total, len(unassigned_doctors),
            )
        self.write(values)
        _logger.debug('Command Center V2 refreshed in %.3fs for companies %s', time.monotonic() - started_at, company_ids)

    def _prepare_branch_lines(self, company_ids, doctors, period_requests, current_open_requests,
                              invoices, payments, funds, activities, complete):
        today = fields.Date.context_today(self)
        rows = []
        for company in self.env['res.company'].browse(company_ids):
            c_doctors = doctors.filtered(lambda r: r.company_id == company)
            c_complete = complete.filtered(lambda r: r.company_id == company)
            c_requests = period_requests.filtered(lambda r: r.company_id == company)
            c_open = current_open_requests.filtered(lambda r: r.company_id == company)
            c_delayed = c_open.filtered(lambda r: r.create_date and r.create_date < fields.Datetime.now() - timedelta(days=7))
            request_ids = set(c_requests.ids)
            c_activities = activities.filtered(lambda a: a.res_id in request_ids)
            completion = self._bounded_percentage(len(c_complete), len(c_doctors))
            delay_rate = len(c_delayed) * 100.0 / len(c_open) if c_open else 0
            unpaid = invoices.filtered(lambda m: m.company_id == company and m.amount_residual > 0)
            c_invoices = invoices.filtered(lambda m: m.company_id == company)
            c_payments = payments.filtered(lambda p: p.company_id == company)
            critical_alerts = (
                int(completion < 60.0)
                + int(delay_rate > 30.0)
                + int(bool(unpaid) and not c_payments)
                + int(bool(c_activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)))
            )
            has_operational_data = bool(
                c_requests
                or c_invoices
                or c_payments
                or c_activities
            )
            has_branch_data = bool(c_doctors or has_operational_data)
            if has_branch_data:
                branch_due, branch_collected, _branch_collection_rate = self._collection_amounts(c_invoices)
                score_details = self._health_score_details(
                    completion, len(c_open), len(c_delayed),
                    branch_due, branch_collected,
                    0, 0, len(c_activities),
                    len(c_activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)),
                    critical_alerts,
                    has_data_quality=bool(c_doctors),
                    has_transactions=bool(c_requests or c_open),
                    has_financial=bool(c_invoices or c_payments),
                    has_tasks=bool(c_activities),
                    has_alerts=True,
                )
                branch_score = score_details['health_score']
                status, status_reason = self._branch_status_values(
                    branch_score, True, completion, delay_rate, bool(unpaid),
                    bool(c_activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)),
                )
                score_label = '%.1f' % branch_score
            else:
                critical_alerts = 0
                empty_score = self._empty_branch_score_values()
                branch_score = empty_score['branch_health_score']
                score_label = empty_score['branch_health_score_label']
                status = empty_score['performance_state']
                status_reason = empty_score['branch_status_reason']
                score_details = {
                    'data_quality_score': 0.0, 'transaction_score': 0.0,
                    'financial_score': 0.0, 'task_score': 0.0, 'alert_score': 0.0,
                    'evaluation_confidence': 'low',
                    'evaluation_confidence_label': _('منخفضة'),
                }
            last_activity = max(c_activities.mapped('write_date'), default=False)
            rows.append((0, 0, {
                'company_id': company.id,
                'doctor_count': len(c_doctors),
                'complete_doctor_count': len(c_complete),
                'completion_rate': completion,
                'open_request_count': len(c_open),
                'delayed_request_count': len(c_delayed),
                'month_revenue': sum(c_invoices.mapped('amount_untaxed_signed')),
                'month_receipts': sum(c_payments.mapped('amount')),
                'unpaid_invoice_total': sum(unpaid.mapped('amount_residual')),
                'fund_count': len(funds.filtered(lambda f: f.company_id == company)),
                'open_task_count': len(c_activities),
                'overdue_task_count': len(c_activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)),
                'last_activity': last_activity,
                'performance_state': status,
                'branch_health_score': branch_score,
                'branch_health_score_label': score_label,
                'has_health_score': has_branch_data,
                'branch_status_reason': status_reason,
                'critical_alerts_count': critical_alerts,
                'data_quality_score': score_details['data_quality_score'],
                'transaction_score': score_details['transaction_score'],
                'financial_score': score_details['financial_score'],
                'task_score': score_details['task_score'],
                'alert_score': score_details['alert_score'],
                'evaluation_confidence': score_details['evaluation_confidence'],
                'evaluation_confidence_label': score_details['evaluation_confidence_label'],
                'currency_id': company.currency_id.id,
            }))
        return rows

    @api.model
    def _branch_status_values(self, score, has_data, completion_rate, delay_rate,
                              has_unpaid, has_overdue_tasks):
        if not has_data:
            return 'insufficient_data', _('لا توجد بيانات أساسية أو حركة تشغيلية.')
        reasons = []
        if completion_rate < 75:
            reasons.append(_('اكتمال البيانات منخفض'))
        if delay_rate > 20:
            reasons.append(_('ارتفاع المعاملات المتأخرة'))
        if has_unpaid:
            reasons.append(_('توجد مبالغ غير محصلة'))
        if has_overdue_tasks:
            reasons.append(_('توجد مهام متأخرة'))
        reason = '، '.join(reasons) or _('المؤشرات الأساسية مستقرة')
        if score >= 90:
            return 'excellent', reason
        if score >= 75:
            return 'good', reason
        if score >= 60:
            return 'follow_up', reason
        return 'struggling', reason

    @api.model
    def _empty_branch_score_values(self):
        return {
            'branch_health_score': False,
            'branch_health_score_label': _('غير متوفر'),
            'has_health_score': False,
            'performance_state': 'insufficient_data',
            'branch_status_reason': _('بيانات غير كافية'),
        }

    @api.model
    def _evaluate_branch_performance(
        self,
        completion_rate,
        delay_rate,
        has_financial_alert,
        doctor_count=0,
        has_operational_data=False,
    ):
        """Return a ratio-based rating only when the sample is meaningful.

        Only a completely empty branch is marked as having insufficient data.
        A branch that has doctors or operational records receives a score.
        The thresholds are intentionally isolated here for later configuration.
        """
        if doctor_count == 0 and not has_operational_data:
            return 'insufficient_data'
        if completion_rate >= 90 and delay_rate <= 5 and not has_financial_alert:
            return 'excellent'
        if completion_rate >= 80 and delay_rate <= 15:
            return 'good'
        if completion_rate >= 60 and delay_rate <= 30:
            return 'follow_up'
        return 'struggling'

    def _prepare_fund_lines(self, funds, ledger):
        total = sum(ledger.mapped('distributed_amount'))
        commands = []
        for fund in funds:
            rows = ledger.filtered(lambda item: item.fund_box_id == fund)
            amount = sum(rows.mapped('distributed_amount'))
            last_movement = max(rows.mapped('invoice_date'), default=False)
            commands.append((0, 0, {
                'fund_box_id': fund.id,
                'company_id': fund.company_id.id,
                'distributed_amount': amount,
                'percentage_of_total': self._bounded_percentage(amount, total),
                'movement_count': len(rows),
                'last_movement_date': last_movement,
                'movement_state': 'active' if rows else 'no_movement',
                'currency_id': fund.company_id.currency_id.id,
            }))
        return commands

    def _prepare_alert_lines(self, delayed_requests, invoices, activities, doctors=None,
                             draft_move_count=0, distribution_issue_count=0,
                             outstanding_invoices=None, reference_date=None,
                             doctor_distribution_matches=True):
        doctors = doctors or self.env['res.partner']
        outstanding = outstanding_invoices if outstanding_invoices is not None else invoices.filtered(
            lambda move: move.amount_residual > 0
        )
        reference_date = reference_date or fields.Date.context_today(self)
        not_due = outstanding.filtered(
            lambda move: move.invoice_date_due and move.invoice_date_due > reference_date
        )
        due_today = outstanding.filtered(lambda move: move.invoice_date_due == reference_date)
        overdue_short = outstanding.filtered(
            lambda move: move.invoice_date_due
            and reference_date - timedelta(days=30) < move.invoice_date_due < reference_date
        )
        overdue_long = outstanding.filtered(
            lambda move: move.invoice_date_due
            and move.invoice_date_due <= reference_date - timedelta(days=30)
        )
        overdue = activities.filtered(lambda a: a.date_deadline and a.date_deadline < fields.Date.context_today(self))
        candidates = [
            ('critical', _('معاملات متأخرة'), len(delayed_requests), _('توجد معاملات تجاوزت مهلة المتابعة.'), 'membership.service.request',
             [('id', 'in', delayed_requests.ids)], 'fa-clock-o'),
            ('critical', _('مهام متأخرة'), len(overdue), _('توجد مهام تجاوزت تاريخ الاستحقاق.'), 'mail.activity',
             [('id', 'in', overdue.ids)], 'fa-calendar-times-o'),
            ('info', _('فواتير غير مدفوعة لم تستحق بعد'), len(not_due), _('مبالغ مفتوحة لم يحل تاريخ استحقاقها بعد.'), 'account.move',
             [('id', 'in', not_due.ids)], 'fa-info-circle'),
            ('warning', _('فواتير مستحقة اليوم'), len(due_today), _('فواتير تحتاج متابعة في تاريخ الاستحقاق الحالي.'), 'account.move',
             [('id', 'in', due_today.ids)], 'fa-calendar-check-o'),
            ('warning', _('فواتير متأخرة'), len(overdue_short), _('فواتير تجاوزت تاريخ الاستحقاق بأقل من 30 يومًا.'), 'account.move',
             [('id', 'in', overdue_short.ids)], 'fa-exclamation-circle'),
            ('critical', _('فواتير متأخرة أكثر من 30 يومًا'), len(overdue_long), _('فواتير تجاوزت تاريخ الاستحقاق بثلاثين يومًا أو أكثر.'), 'account.move',
             [('id', 'in', overdue_long.ids)], 'fa-exclamation-triangle'),
            ('warning', _('أطباء بدون اختصاص'), len(doctors.filtered(lambda d: not d.medical_specialty_id)), _('ملفات تحتاج استكمال الاختصاص.'), 'res.partner',
             [('id', 'in', doctors.filtered(lambda d: not d.medical_specialty_id).ids)], 'fa-user-md'),
            ('warning', _('أطباء بدون رقم وطني'), len(doctors.filtered(lambda d: not d.national_id)), _('ملفات تحتاج استكمال الرقم الوطني.'), 'res.partner',
             [('id', 'in', doctors.filtered(lambda d: not d.national_id).ids)], 'fa-id-card-o'),
            ('warning', _('أطباء بدون هاتف'), len(doctors.filtered(lambda d: not d.phone and not d.mobile)), _('ملفات بدون وسيلة اتصال.'), 'res.partner',
             [('id', 'in', doctors.filtered(lambda d: not d.phone and not d.mobile).ids)], 'fa-phone'),
            ('warning', _('قيود غير مرحلة'), draft_move_count, _('توجد قيود محاسبية ما زالت في المسودة.'), 'account.move',
             [('state', '=', 'draft')], 'fa-book'),
            ('critical', _('مشكلات توزيع الإيرادات'), distribution_issue_count, _('طلبات تحتاج تصحيح إعداد التوزيع.'), 'membership.service.request',
             [('revenue_distribution_required', '=', True), ('revenue_distribution_ready', '=', False)], 'fa-exclamation-triangle'),
            ('critical', _('عدم تطابق توزيع سجلات الأطباء'), int(not doctor_distribution_matches), _('إجمالي الأطباء لا يساوي مجموع أطباء الشركات المسموحة مع الأطباء غير المرتبطين بنقابة فرعية.'), 'res.partner',
             [('id', 'in', doctors.ids)], 'fa-users'),
        ]
        severity_order = {'critical': 0, 'warning': 1, 'info': 2, 'success': 3}
        rows = []
        for severity, name, count, message, model, domain, icon in candidates:
            if not count:
                continue
            rows.append((0, 0, {
                'name': name, 'alert_type': model.replace('.', '_'), 'severity': severity,
                'count': count, 'message': message, 'action_model': model,
                'action_domain': repr(domain),
                'sequence': -1 if name == _('عدم تطابق توزيع سجلات الأطباء')
                else severity_order[severity] * 100 + len(rows),
                'icon': icon,
            }))
        return sorted(rows, key=lambda command: command[2]['sequence'])[:6]

    def _prepare_employee_lines(self, requests, activities):
        request_map = defaultdict(lambda: self.env['membership.service.request'])
        for request in requests:
            user = request.started_by_id or request.submitted_by_id or request.completed_by_id
            if user:
                request_map[user] |= request
        commands = []
        today = fields.Date.context_today(self)
        for user, user_requests in request_map.items():
            completed = user_requests.filtered(lambda r: r.state == 'completed')
            delayed = user_requests.filtered(
                lambda r: r.state not in ('completed', 'cancelled')
                and r.create_date and r.create_date < fields.Datetime.now() - timedelta(days=7)
            )
            user_activities = activities.filtered(lambda a: a.user_id == user)
            overdue_tasks = user_activities.filtered(lambda a: a.date_deadline and a.date_deadline < today)
            commands.append((0, 0, {
                'user_id': user.id,
                'employee_name': self._user_display_name(user),
                'company_id': user.company_id.id,
                'assigned_count': len(user_requests),
                'completed_count': len(completed),
                'delayed_count': len(delayed),
                'completion_rate': self._bounded_percentage(len(completed), len(user_requests)),
                'open_task_count': len(user_activities),
                'overdue_task_count': len(overdue_tasks),
                'last_activity': max(user_requests.mapped('write_date'), default=False),
                'performance_state': 'follow_up' if delayed or overdue_tasks else 'good',
            }))
        return commands

    @api.model
    def _user_display_name(self, user):
        employee = user.employee_id if 'employee_id' in user._fields else False
        return employee.name if employee else user.name

    def _event_display_values(self, event_date, user):
        localized = fields.Datetime.context_timestamp(self, event_date) if event_date else False
        return {
            'employee_name': self._user_display_name(user),
            'event_date_display': localized.strftime('%d-%m-%Y') if localized else _('غير متوفر'),
            'event_time_display': localized.strftime('%H:%M') if localized else _('غير متوفر'),
        }

    def _prepare_event_lines(self, requests, invoices, payments, ledger):
        rows = []
        for request in requests[:20]:
            values = {
                'event_type': 'request', 'description': _('تحديث المعاملة %s') % request.display_name,
                'company_id': request.company_id.id, 'user_id': request.write_uid.id,
                'event_date': request.write_date, 'res_model': request._name, 'res_id': request.id,
            }
            values.update(self._event_display_values(request.write_date, request.write_uid))
            rows.append((request.write_date, values))
        for invoice in invoices[:15]:
            values = {
                'event_type': 'invoice', 'description': _('تحديث الفاتورة %s') % invoice.display_name,
                'company_id': invoice.company_id.id, 'user_id': invoice.write_uid.id,
                'event_date': invoice.write_date, 'res_model': invoice._name, 'res_id': invoice.id,
            }
            values.update(self._event_display_values(invoice.write_date, invoice.write_uid))
            rows.append((invoice.write_date, values))
        for payment in payments[:15]:
            values = {
                'event_type': 'payment', 'description': _('تسجيل قبض %s') % payment.display_name,
                'company_id': payment.company_id.id, 'user_id': payment.write_uid.id,
                'event_date': payment.write_date, 'res_model': payment._name, 'res_id': payment.id,
            }
            values.update(self._event_display_values(payment.write_date, payment.write_uid))
            rows.append((payment.write_date, values))
        for item in ledger[:15]:
            values = {
                'event_type': 'distribution', 'description': _('توزيع إيراد على %s') % item.fund_box_id.display_name,
                'company_id': item.company_id.id, 'user_id': item.write_uid.id,
                'event_date': item.write_date, 'res_model': item._name, 'res_id': item.id,
            }
            values.update(self._event_display_values(item.write_date, item.write_uid))
            rows.append((item.write_date, values))
        rows = sorted(rows, key=lambda row: row[0] or fields.Datetime.now(), reverse=True)[:20]
        return [(0, 0, values) for _date, values in rows]

    def _open(self, model, name, domain):
        company_ids = self._allowed_company_ids(self.company_id)
        return self._workspace_action(model, name, [('company_id', 'in', company_ids)] + domain)

    def action_open_doctors(self):
        company_ids = self._allowed_company_ids(self.company_id)
        domain = self._doctor_scope_domain(
            company_ids, include_unassigned=not bool(self.company_id),
        )
        return self._workspace_action('res.partner', _('الأطباء'), domain)

    def action_open_incomplete_doctors(self):
        ids = self._allowed_company_ids(self.company_id)
        domains = self._doctor_quality_domains(
            ids, include_unassigned=not bool(self.company_id),
        )
        return self._workspace_action('res.partner', _('الملفات الناقصة'), domains['incomplete'])

    def action_open_unassigned_doctors(self):
        self.ensure_one()
        if self.company_id:
            return self._workspace_action('res.partner', _('أطباء غير مرتبطين بنقابة فرعية'), [('id', '=', 0)])
        return self._workspace_action(
            'res.partner',
            _('أطباء غير مرتبطين بنقابة فرعية'),
            self._doctor_unassigned_domain(),
        )

    def action_open_open_requests(self):
        company_ids = self._allowed_company_ids(self.company_id)
        domain = self._service_request_base_domain(company_ids)
        domain.append(('state', 'not in', ('completed', 'cancelled')))
        return self._workspace_action('membership.service.request', _('الطلبات المفتوحة حاليًا'), domain)

    def action_open_delayed_requests(self):
        company_ids = self._allowed_company_ids(self.company_id)
        domain = self._service_request_base_domain(company_ids)
        domain += [
            ('state', 'not in', ('completed', 'cancelled')),
            ('create_date', '<', fields.Datetime.now() - timedelta(days=7)),
        ]
        return self._workspace_action('membership.service.request', _('الطلبات المفتوحة المتأخرة'), domain)

    def action_open_unpaid_invoices(self):
        return self._open('account.move', _('الفواتير غير المحصلة'), [
            ('move_type', '=', 'out_invoice'),
            ('membership_service_request_id', '!=', False),
            ('state', '=', 'posted'),
            ('amount_residual', '>', 0),
        ] + self._date_domain('invoice_date'))

    def action_open_overdue_tasks(self):
        company_ids = self._allowed_company_ids(self.company_id)
        request_domain = self._service_request_base_domain(company_ids)
        period_requests = self.env['membership.service.request'].search(
            request_domain + self._datetime_domain('create_date')
        )
        open_requests = self.env['membership.service.request'].search(
            request_domain + [('state', 'not in', ('completed', 'cancelled'))]
        )
        completed_requests = self.env['membership.service.request'].search(
            request_domain + [('state', '=', 'completed')]
            + self._datetime_domain('completed_date')
        )
        request_ids = (period_requests | open_requests | completed_requests).ids
        return self._workspace_action('mail.activity', _('المهام المتأخرة'), [
            ('res_model', '=', 'membership.service.request'),
            ('res_id', 'in', request_ids or [0]),
            ('date_deadline', '<', fields.Date.context_today(self)),
        ])


class MembershipCommandCenterBranchLine(models.TransientModel):
    _name = 'membership.command.center.branch.line'
    _description = 'أداء النقابات الفرعية'
    center_id = fields.Many2one('membership.command.center', required=True, ondelete='cascade')
    company_id = fields.Many2one('res.company', string='النقابة الفرعية', readonly=True)
    doctor_count = fields.Integer(string='الأطباء', readonly=True)
    complete_doctor_count = fields.Integer(string='الملفات المكتملة', readonly=True)
    completion_rate = fields.Float(string='اكتمال البيانات %', readonly=True)
    open_request_count = fields.Integer(string='الطلبات المفتوحة', readonly=True)
    delayed_request_count = fields.Integer(string='المتأخرات', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    month_revenue = fields.Monetary(string='إيرادات الشهر', currency_field='currency_id', readonly=True)
    month_receipts = fields.Monetary(string='المقبوضات', currency_field='currency_id', readonly=True)
    unpaid_invoice_total = fields.Monetary(string='غير المحصل', currency_field='currency_id', readonly=True)
    fund_count = fields.Integer(string='الصناديق', readonly=True)
    open_task_count = fields.Integer(string='المهام المفتوحة', readonly=True)
    overdue_task_count = fields.Integer(string='المهام المتأخرة', readonly=True)
    last_activity = fields.Datetime(string='آخر نشاط', readonly=True)
    performance_state = fields.Selection([
        ('insufficient_data', 'بيانات غير كافية'),
        ('excellent', 'ممتاز'), ('good', 'جيد'),
        ('follow_up', 'يحتاج متابعة'), ('struggling', 'متعثر'),
    ], string='حالة الأداء', readonly=True)
    branch_health_score = fields.Float(string='درجة الصحة', readonly=True)
    branch_health_score_label = fields.Char(string='درجة الصحة', readonly=True)
    has_health_score = fields.Boolean(string='تتوفر درجة صحة', readonly=True)
    data_quality_score = fields.Float(string='جودة البيانات', readonly=True)
    transaction_score = fields.Float(string='المعاملات', readonly=True)
    financial_score = fields.Float(string='المالية', readonly=True)
    task_score = fields.Float(string='المهام', readonly=True)
    alert_score = fields.Float(string='التنبيهات', readonly=True)
    evaluation_confidence = fields.Selection([
        ('high', 'مرتفعة'), ('medium', 'متوسطة'), ('low', 'منخفضة'),
    ], string='ثقة التقييم', readonly=True)
    evaluation_confidence_label = fields.Char(string='ثقة التقييم', readonly=True)
    branch_status_reason = fields.Char(string='سبب الحالة', readonly=True)
    critical_alerts_count = fields.Integer(string='التنبيهات الحرجة', readonly=True)

    def action_open_branch(self):
        self.ensure_one()
        if self.company_id not in self.env.companies:
            raise AccessError(_('لا تملك صلاحية الوصول إلى هذه النقابة الفرعية.'))
        center = self.env['membership.command.center'].create({
            'company_id': self.company_id.id,
            'date_from': self.center_id.date_from,
            'date_to': self.center_id.date_to,
        })
        center._refresh_values()
        return {'type': 'ir.actions.act_window', 'name': _('مركز الفرع'), 'res_model': center._name, 'res_id': center.id, 'view_mode': 'form', 'target': 'current'}

    def action_open_branch_doctors(self):
        """Expose the exact records used by the branch doctor KPI."""
        self.ensure_one()
        if self.company_id not in self.env.companies:
            raise AccessError(_('لا تملك صلاحية الوصول إلى هذه النقابة الفرعية.'))
        return self.center_id._workspace_action(
            'res.partner',
            _('أطباء %s') % self.company_id.display_name,
            [
                ('is_doctor', '=', True),
                ('company_id', '=', self.company_id.id),
            ],
            context={
                'default_is_doctor': True,
                'default_company_id': self.company_id.id,
            },
        )


class MembershipCommandCenterFundLine(models.TransientModel):
    _name = 'membership.command.center.fund.line'
    _description = 'ملخص صناديق مركز القيادة'
    center_id = fields.Many2one('membership.command.center', required=True, ondelete='cascade')
    fund_box_id = fields.Many2one('syndicate.fund.box', string='الصندوق', readonly=True)
    company_id = fields.Many2one('res.company', string='النقابة الفرعية', readonly=True)
    currency_id = fields.Many2one('res.currency', readonly=True)
    distributed_amount = fields.Monetary(string='الإيراد الموزع', currency_field='currency_id', readonly=True)
    percentage_of_total = fields.Float(string='نسبة من الإجمالي', readonly=True)
    movement_count = fields.Integer(string='عدد الحركات', readonly=True)
    last_movement_date = fields.Date(string='آخر حركة', readonly=True)
    movement_state = fields.Selection([
        ('active', 'توجد حركة'),
        ('no_movement', 'بدون حركة'),
    ], string='حالة الصندوق', readonly=True)

    def action_open_fund(self):
        self.ensure_one()
        return self.center_id._workspace_revenue_ledger_action(
            _('حركات الصندوق'), [('fund_box_id', '=', self.fund_box_id.id)]
        )


class MembershipCommandCenterAlertLine(models.TransientModel):
    _name = 'membership.command.center.alert.line'
    _description = 'تنبيهات مركز القيادة'
    center_id = fields.Many2one('membership.command.center', required=True, ondelete='cascade')
    severity = fields.Selection([
        ('critical', 'حرج'), ('warning', 'يحتاج متابعة'),
        ('info', 'معلومات'), ('success', 'طبيعي'),
    ], string='درجة الخطورة', readonly=True)
    name = fields.Char(string='التنبيه', readonly=True)
    alert_type = fields.Char(string='نوع التنبيه', readonly=True)
    count = fields.Integer(string='العدد', readonly=True)
    message = fields.Char(string='التفاصيل', readonly=True)
    company_id = fields.Many2one('res.company', string='النقابة الفرعية', readonly=True)
    action_model = fields.Char(readonly=True)
    action_domain = fields.Text(readonly=True)
    sequence = fields.Integer(readonly=True)
    icon = fields.Char(readonly=True)
    responsible_user_id = fields.Many2one('res.users', string='المسؤول', readonly=True)
    due_date = fields.Date(string='الاستحقاق', readonly=True)

    def action_open_alert(self):
        self.ensure_one()
        if not self.action_model:
            return False
        allowed_ids = self.center_id._allowed_company_ids(self.center_id.company_id)
        domain = safe_eval(self.action_domain or '[]')
        if self.action_model != 'res.partner' and 'company_id' in self.env[self.action_model]._fields:
            domain = [('company_id', 'in', allowed_ids)] + domain
        return self.center_id._workspace_action(
            self.action_model, self.name, domain,
            context={'allowed_company_ids': allowed_ids},
        )


class MembershipCommandCenterEmployeeLine(models.TransientModel):
    _name = 'membership.command.center.employee.line'
    _description = 'أداء الموظفين في مركز القيادة'

    center_id = fields.Many2one('membership.command.center', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='الموظف', readonly=True)
    employee_name = fields.Char(string='الموظف', readonly=True)
    company_id = fields.Many2one('res.company', string='النقابة الفرعية', readonly=True)
    assigned_count = fields.Integer(string='المعاملات المسندة', readonly=True)
    completed_count = fields.Integer(string='المعاملات المنجزة', readonly=True)
    delayed_count = fields.Integer(string='المعاملات المتأخرة', readonly=True)
    completion_rate = fields.Float(string='نسبة الإنجاز %', readonly=True)
    open_task_count = fields.Integer(string='المهام المفتوحة', readonly=True)
    overdue_task_count = fields.Integer(string='المهام المتأخرة', readonly=True)
    last_activity = fields.Datetime(string='آخر نشاط', readonly=True)
    performance_state = fields.Selection([
        ('good', 'جيد'), ('follow_up', 'يحتاج متابعة'),
    ], string='حالة الأداء', readonly=True)


class MembershipCommandCenterEventLine(models.TransientModel):
    _name = 'membership.command.center.event.line'
    _description = 'آخر أحداث مركز القيادة'
    _order = 'event_date desc, id desc'

    center_id = fields.Many2one('membership.command.center', required=True, ondelete='cascade')
    event_type = fields.Selection([
        ('request', 'معاملة'), ('invoice', 'فاتورة'),
        ('payment', 'قبض'), ('distribution', 'توزيع إيراد'),
    ], string='نوع الحدث', readonly=True)
    description = fields.Char(string='الوصف', readonly=True)
    company_id = fields.Many2one('res.company', string='النقابة الفرعية', readonly=True)
    user_id = fields.Many2one('res.users', string='المستخدم', readonly=True)
    employee_name = fields.Char(string='الموظف', readonly=True)
    event_date = fields.Datetime(string='التاريخ والوقت', readonly=True)
    event_date_display = fields.Char(string='التاريخ', readonly=True)
    event_time_display = fields.Char(string='الوقت', readonly=True)
    res_model = fields.Char(readonly=True)
    res_id = fields.Integer(readonly=True)

    def action_open_event(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        record = self.env[self.res_model].browse(self.res_id).exists()
        if not record:
            return False
        if 'company_id' in record._fields and record.company_id not in self.env.companies:
            raise AccessError(_('لا تملك صلاحية الوصول إلى هذا السجل.'))
        return self.center_id._workspace_open_record(self.description, self.res_model, record)
