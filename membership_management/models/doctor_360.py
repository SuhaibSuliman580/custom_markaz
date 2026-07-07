import re

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError


class MembershipDoctor360(models.TransientModel):
    _name = 'membership.doctor.360'
    _description = 'الملف الموحد للطبيب'
    _rec_name = 'display_name'

    display_name = fields.Char(string='العنوان', default='الملف الموحد للطبيب', readonly=True)
    doctor_id = fields.Many2one(
        'res.partner',
        string='الطبيب',
        domain="[('is_doctor', '=', True)]",
    )
    doctor_image_1920 = fields.Image(related='doctor_id.image_1920', string='صورة الطبيب', readonly=True)
    company_id = fields.Many2one(related='doctor_id.company_id', string='الشركة / النقابة الفرعية', readonly=True)
    membership_number = fields.Char(related='doctor_id.membership_number', string='رقم العضوية', readonly=True)
    membership_state = fields.Selection(related='doctor_id.doctor_membership_state', string='حالة العضوية', readonly=True)
    active_membership_id = fields.Many2one(related='doctor_id.active_membership_id', string='العضوية النشطة', readonly=True)
    membership_start_date = fields.Date(related='doctor_id.membership_start_date', string='تاريخ بداية العضوية', readonly=True)
    membership_end_date = fields.Date(related='doctor_id.membership_end_date', string='تاريخ نهاية العضوية', readonly=True)
    last_renewal_date = fields.Date(string='تاريخ آخر تجديد', readonly=True)
    phone = fields.Char(related='doctor_id.phone', string='الهاتف', readonly=True)
    email = fields.Char(related='doctor_id.email', string='البريد الإلكتروني', readonly=True)
    medical_specialty_id = fields.Many2one(related='doctor_id.medical_specialty_id', string='الاختصاص', readonly=True)
    university_id = fields.Many2one(related='doctor_id.university_id', string='الجامعة', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)

    open_request_count = fields.Integer(string='طلبات خدمات مفتوحة', readonly=True)
    waiting_finance_count = fields.Integer(string='بانتظار المالية', readonly=True)
    waiting_payment_count = fields.Integer(string='بانتظار الدفع', readonly=True)
    paid_ready_count = fields.Integer(string='مدفوعة جاهزة للتنفيذ', readonly=True)
    completed_request_count = fields.Integer(string='طلبات منجزة', readonly=True)
    unpaid_invoice_count = fields.Integer(string='فواتير غير مدفوعة', readonly=True)
    residual_total = fields.Monetary(string='إجمالي المستحقات المتبقية', currency_field='currency_id', readonly=True)
    subscription_year_count = fields.Integer(string='إجمالي سنوات الاشتراك', readonly=True)
    unpaid_subscription_year_count = fields.Integer(string='عدد السنوات غير المدفوعة', readonly=True)

    service_request_line_ids = fields.One2many('membership.doctor.360.service.line', 'dashboard_id', string='طلبات الخدمات', readonly=True)
    period_line_ids = fields.One2many('membership.doctor.360.period.line', 'dashboard_id', string='العضوية', readonly=True)
    invoice_line_ids = fields.One2many('membership.doctor.360.invoice.line', 'dashboard_id', string='الفواتير', readonly=True)
    payment_line_ids = fields.One2many('membership.doctor.360.payment.line', 'dashboard_id', string='المدفوعات', readonly=True)
    activity_line_ids = fields.One2many('membership.doctor.360.activity.line', 'dashboard_id', string='النشاطات', readonly=True)
    timeline_line_ids = fields.One2many('membership.doctor.360.timeline.line', 'dashboard_id', string='المسار الزمني', readonly=True)
    document_line_ids = fields.One2many('membership.doctor.360.document.line', 'dashboard_id', string='الوثائق', readonly=True)

    has_doctor = fields.Boolean(string='تم اختيار طبيب', readonly=True)
    membership_expired_alert = fields.Boolean(string='تنبيه انتهاء العضوية', readonly=True)
    has_unpaid_fees_alert = fields.Boolean(string='تنبيه مستحقات مالية', readonly=True)
    has_open_requests_alert = fields.Boolean(string='تنبيه طلبات مفتوحة', readonly=True)
    has_service_requests = fields.Boolean(string='توجد طلبات خدمات', readonly=True)
    has_periods = fields.Boolean(string='توجد عضويات', readonly=True)
    has_invoices = fields.Boolean(string='توجد فواتير', readonly=True)
    has_payments = fields.Boolean(string='توجد مدفوعات', readonly=True)
    has_activities = fields.Boolean(string='توجد نشاطات', readonly=True)
    has_timeline = fields.Boolean(string='يوجد مسار زمني', readonly=True)
    has_documents = fields.Boolean(string='توجد وثائق', readonly=True)
    show_new_membership_button = fields.Boolean(string='إظهار زر انتساب جديد', readonly=True)
    show_renew_membership_button = fields.Boolean(string='إظهار زر تجديد العضوية', readonly=True)
    show_follow_request_button = fields.Boolean(string='إظهار زر متابعة الطلب الحالي', readonly=True)
    show_open_invoice_button = fields.Boolean(string='إظهار زر فتح الفاتورة', readonly=True)
    show_create_service_button = fields.Boolean(string='إظهار زر إنشاء طلب خدمة', readonly=True)
    current_open_request_id = fields.Many2one('membership.service.request', string='الطلب الحالي', readonly=True)
    current_unpaid_invoice_id = fields.Many2one('account.move', string='الفاتورة غير المدفوعة', readonly=True)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        doctor = self._get_context_doctor()
        vals.update({'display_name': _('الملف الموحد للطبيب')})
        vals.update(self._prepare_dashboard_values(doctor))
        return vals

    @api.model
    def _get_context_doctor(self):
        doctor_id = self.env.context.get('default_doctor_id')
        if doctor_id:
            return self.env['res.partner'].browse(doctor_id)
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')
        if active_model == 'res.partner' and active_id:
            return self.env['res.partner'].browse(active_id)
        if active_model == 'membership.service.request' and active_id:
            return self.env['membership.service.request'].browse(active_id).partner_id
        return self.env['res.partner']

    @api.model
    def action_open_doctor_360(self):
        doctor = self._get_context_doctor()
        vals = self._prepare_dashboard_values(doctor)
        dashboard = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('الملف الموحد للطبيب'),
            'res_model': 'membership.doctor.360',
            'res_id': dashboard.id,
            'view_mode': 'form',
            'view_id': self.env.ref('membership_management.view_membership_doctor_360_form').id,
            'target': 'current',
        }

    @api.model
    def action_open_for_doctor(self, doctor):
        return self.with_context(default_doctor_id=doctor.id).action_open_doctor_360()

    def action_reload_doctor(self):
        self.ensure_one()
        vals = self._prepare_dashboard_values(self.doctor_id)
        for field_name in (
            'service_request_line_ids',
            'period_line_ids',
            'invoice_line_ids',
            'payment_line_ids',
            'activity_line_ids',
            'timeline_line_ids',
            'document_line_ids',
        ):
            vals[field_name] = [(5, 0, 0)] + vals.get(field_name, [])
        self.write(vals)
        return True

    @api.model
    def _company_domain(self):
        return [('company_id', 'in', self.env.companies.ids)]

    @api.model
    def _prepare_dashboard_values(self, doctor=False):
        currency = self.env.company.currency_id
        if not doctor:
            return {
                'currency_id': currency.id,
                'has_doctor': False,
            }

        service_requests = self.env['membership.service.request'].search(
            [('partner_id', '=', doctor.id)] + self._company_domain(),
            order='create_date desc, id desc',
        )
        periods = self.env['membership.period'].search(
            [('partner_id', '=', doctor.id), ('company_id', 'in', self.env.companies.ids)],
            order='start_date desc, id desc',
        )
        invoices = self._get_doctor_invoices(doctor)
        payments = self._get_doctor_payments(doctor)
        activities = self._prepare_activity_commands(service_requests, periods, invoices)
        timeline = self._prepare_timeline_commands(service_requests)
        documents = self._prepare_document_commands(doctor, service_requests, periods)
        can_read_invoices = self._can_read_model('account.move')
        last_renewal_period = periods.filtered(lambda period: period.period_type == 'renewal')[:1] or periods[:1]

        service_commands = [(0, 0, self._service_line_values(request, can_read_invoices)) for request in service_requests]
        payment_dates_by_invoice = self._get_invoice_payment_dates(payments)
        period_commands = [
            (0, 0, self._period_line_values(period, can_read_invoices, payment_dates_by_invoice))
            for period in periods
        ]
        invoice_commands = [(0, 0, self._invoice_line_values(invoice)) for invoice in invoices]
        payment_commands = [(0, 0, self._payment_line_values(payment, doctor)) for payment in payments]

        unpaid_invoices = invoices.filtered(lambda inv: inv.payment_state in ('not_paid', 'partial', 'in_payment') and inv.amount_residual > 0)
        open_requests = service_requests.filtered(lambda req: req.state not in ('completed', 'cancelled'))
        no_membership = not doctor.active_membership_id and doctor.doctor_membership_state in (False, 'none')
        expired_membership = bool(
            doctor.doctor_membership_state == 'expired'
            or (doctor.membership_end_date and doctor.membership_end_date < fields.Date.context_today(self))
        )
        has_special_action = bool(no_membership or expired_membership or open_requests or unpaid_invoices)
        return {
            'display_name': _('الملف الموحد للطبيب'),
            'doctor_id': doctor.id,
            'currency_id': (doctor.company_id.currency_id or currency).id,
            'has_doctor': True,
            'last_renewal_date': last_renewal_period.start_date if last_renewal_period else False,
            'open_request_count': len(open_requests),
            'waiting_finance_count': len(service_requests.filtered(lambda req: req.state == 'waiting_financial_approval')),
            'waiting_payment_count': len(service_requests.filtered(lambda req: req.state == 'waiting_payment')),
            'paid_ready_count': len(service_requests.filtered(lambda req: req.state == 'paid')),
            'completed_request_count': len(service_requests.filtered(lambda req: req.state == 'completed')),
            'unpaid_invoice_count': len(unpaid_invoices),
            'residual_total': sum(unpaid_invoices.mapped('amount_residual')),
            'subscription_year_count': len(periods),
            'unpaid_subscription_year_count': self._get_unpaid_subscription_year_count(periods, can_read_invoices),
            'membership_expired_alert': expired_membership,
            'has_unpaid_fees_alert': bool(unpaid_invoices),
            'has_open_requests_alert': bool(open_requests),
            'show_new_membership_button': no_membership,
            'show_renew_membership_button': expired_membership and not no_membership,
            'show_follow_request_button': bool(open_requests),
            'show_open_invoice_button': bool(unpaid_invoices),
            'show_create_service_button': not has_special_action,
            'current_open_request_id': open_requests[:1].id if open_requests else False,
            'current_unpaid_invoice_id': unpaid_invoices[:1].id if unpaid_invoices else False,
            'has_service_requests': bool(service_commands),
            'has_periods': bool(period_commands),
            'has_invoices': bool(invoice_commands),
            'has_payments': bool(payment_commands),
            'has_activities': bool(activities),
            'has_timeline': bool(timeline),
            'has_documents': bool(documents),
            'service_request_line_ids': service_commands,
            'period_line_ids': period_commands,
            'invoice_line_ids': invoice_commands,
            'payment_line_ids': payment_commands,
            'activity_line_ids': activities,
            'timeline_line_ids': timeline,
            'document_line_ids': documents,
        }

    def _can_read_model(self, model_name):
        try:
            self.env[model_name].check_access_rights('read')
            return True
        except AccessError:
            return False

    def _get_doctor_invoices(self, doctor):
        try:
            return self.env['account.move'].search([
                ('move_type', '=', 'out_invoice'),
                ('partner_id', '=', doctor.id),
                ('company_id', 'in', self.env.companies.ids),
            ], order='invoice_date desc, id desc')
        except AccessError:
            return self.env['account.move']

    def _get_doctor_payments(self, doctor):
        try:
            return self.env['account.payment'].search([
                ('partner_id', '=', doctor.id),
                ('payment_type', '=', 'inbound'),
                ('state', '=', 'posted'),
                ('company_id', 'in', self.env.companies.ids),
            ], order='date desc, id desc', limit=80)
        except AccessError:
            return self.env['account.payment']

    def _service_line_values(self, request, can_read_invoices=True):
        return {
            'service_request_id': request.id,
            'service_type_id': request.service_type_id.id,
            'state': request.state,
            'invoice_payment_state': request.invoice_payment_state,
            'invoice_id': request.invoice_id.id if can_read_invoices else False,
            'request_create_date': request.create_date,
            'last_update_date': request.write_date,
        }

    def _get_invoice_payment_dates(self, payments):
        payment_dates_by_invoice = {}
        for payment in payments:
            for invoice in payment.reconciled_invoice_ids:
                if not payment_dates_by_invoice.get(invoice.id) or payment.date > payment_dates_by_invoice[invoice.id]:
                    payment_dates_by_invoice[invoice.id] = payment.date
        return payment_dates_by_invoice

    def _get_unpaid_subscription_year_count(self, periods, can_read_invoices=True):
        unpaid_count = 0
        for period in periods:
            invoice = period.invoice_id if can_read_invoices else False
            if not invoice:
                unpaid_count += 1
            elif invoice.payment_state not in ('paid', 'in_payment') and invoice.amount_residual > 0:
                unpaid_count += 1
        return unpaid_count

    def _get_subscription_payment_state(self, invoice, can_read_invoices=True):
        if not can_read_invoices or not invoice:
            return 'no_invoice'
        payment_state = invoice.payment_state or 'not_paid'
        if payment_state not in ('not_paid', 'in_payment', 'paid', 'partial', 'reversed', 'blocked'):
            return 'not_paid'
        return payment_state

    def _period_line_values(self, period, can_read_invoices=True, payment_dates_by_invoice=None):
        payment_dates_by_invoice = payment_dates_by_invoice or {}
        invoice = period.invoice_id if can_read_invoices else False
        payment_state = self._get_subscription_payment_state(invoice, can_read_invoices)
        payment_date = payment_dates_by_invoice.get(invoice.id) if invoice else False
        subscription_year = False
        if period.start_date:
            subscription_year = str(period.start_date.year)
        elif period.end_date:
            subscription_year = str(period.end_date.year)
        return {
            'period_id': period.id,
            'name': period.name,
            'subscription_year': subscription_year,
            'start_date': period.start_date,
            'end_date': period.end_date,
            'state': period.state,
            'invoice_id': invoice.id if invoice else False,
            'payment_state': payment_state,
            'payment_date': payment_date,
        }

    def _invoice_line_values(self, invoice):
        return {
            'invoice_id': invoice.id,
            'invoice_date': invoice.invoice_date,
            'origin': invoice.invoice_origin,
            'service_request_id': invoice.membership_service_request_id.id,
            'amount_total': invoice.amount_total,
            'amount_residual': invoice.amount_residual,
            'payment_state': invoice.payment_state,
            'currency_id': invoice.currency_id.id,
        }

    def _payment_line_values(self, payment, doctor):
        invoices = payment.reconciled_invoice_ids.filtered(lambda inv: inv.partner_id == doctor)
        return {
            'payment_id': payment.id,
            'payment_date': payment.date,
            'amount': payment.amount,
            'journal_id': payment.journal_id.id,
            'invoice_names': ', '.join(invoices.mapped('name')),
            'currency_id': payment.currency_id.id,
        }

    def _prepare_activity_commands(self, service_requests, periods, invoices):
        rows = []
        for request in service_requests[:20]:
            rows.append((request.write_date, {
                'activity_date': request.write_date,
                'source_label': _('طلب خدمة'),
                'summary': self._request_summary(request),
                'service_request_id': request.id,
            }))
        for invoice in invoices[:20]:
            rows.append((invoice.write_date, {
                'activity_date': invoice.write_date,
                'source_label': _('فاتورة'),
                'summary': _('فاتورة %(name)s - حالة الدفع: %(state)s') % {
                    'name': invoice.name,
                    'state': dict(invoice._fields['payment_state'].selection).get(invoice.payment_state, invoice.payment_state),
                },
                'invoice_id': invoice.id,
            }))
        for period in periods[:20]:
            rows.append((period.write_date, {
                'activity_date': period.write_date,
                'source_label': _('عضوية'),
                'summary': _('عضوية %(name)s - الحالة: %(state)s') % {
                    'name': period.name,
                    'state': dict(period._fields['state'].selection).get(period.state, period.state),
                },
                'period_id': period.id,
            }))
        rows = sorted(rows, key=lambda item: item[0] or fields.Datetime.now(), reverse=True)[:20]
        return [(0, 0, values) for _date, values in rows]

    def _prepare_timeline_commands(self, service_requests):
        events = []
        for request in service_requests:
            request_label = request.name or _('طلب خدمة')
            self._add_timeline_event(
                events,
                request.create_date,
                request,
                'created',
                _('إنشاء الطلب'),
                _('تم إنشاء الطلب %(request)s') % {'request': request_label},
            )
            self._add_timeline_event(
                events,
                request.submitted_date,
                request,
                'submitted',
                _('إرساله للمالية'),
                _('تم إرسال الطلب %(request)s إلى المالية') % {'request': request_label},
            )
            self._add_timeline_event(
                events,
                request.financial_approved_date,
                request,
                'finance_approved',
                _('اعتماد المالية'),
                _('تم اعتماد الطلب %(request)s مالياً') % {'request': request_label},
            )
            invoice_date = request.invoice_id.create_date or request.invoice_id.date if request.invoice_id else False
            self._add_timeline_event(
                events,
                invoice_date,
                request,
                'invoice_created',
                _('إنشاء الفاتورة'),
                _('تم إنشاء الفاتورة %(invoice)s للطلب %(request)s') % {
                    'invoice': request.invoice_id.name if request.invoice_id else '',
                    'request': request_label,
                },
                request.invoice_id,
            )
            paid_date = request.paid_date
            if not paid_date and request.invoice_id and request.invoice_id.payment_state in ('paid', 'in_payment'):
                paid_date = request.invoice_id.write_date
            self._add_timeline_event(
                events,
                paid_date,
                request,
                'payment_registered',
                _('تسجيل القبض'),
                _('تم تسجيل القبض للطلب %(request)s') % {'request': request_label},
                request.invoice_id,
            )
            self._add_timeline_event(
                events,
                request.started_date,
                request,
                'service_started',
                _('بدء التنفيذ'),
                _('بدأ تنفيذ الخدمة للطلب %(request)s') % {'request': request_label},
            )
            self._add_timeline_event(
                events,
                request.completed_date,
                request,
                'service_completed',
                _('إنهاء الخدمة'),
                _('تم إنهاء الخدمة للطلب %(request)s') % {'request': request_label},
            )

        events = sorted(events, key=lambda item: item[0])
        return [(0, 0, values) for _date, values in events]

    def _prepare_document_commands(self, doctor, service_requests, periods):
        rows = []
        for request in service_requests.filtered(lambda req: req.state == 'completed'):
            doc_type = self._guess_document_type(request.service_type_id.name or '')
            if not doc_type:
                continue
            rows.append((request.completed_date or request.write_date or request.create_date, {
                'document_type': doc_type,
                'name': request.service_type_id.display_name,
                'source_model': _('طلب خدمة'),
                'issue_date': request.completed_date or request.write_date,
                'service_request_id': request.id,
                'company_id': request.company_id.id,
            }))

        for attachment in self._get_doctor_document_attachments(doctor, service_requests, periods):
            doc_type = self._guess_document_type(attachment.name or '') or _('وثيقة')
            request = service_requests.filtered(lambda req: attachment in req.attachment_ids)[:1]
            period = periods.filtered(lambda membership: attachment.res_model == 'membership.period' and attachment.res_id == membership.id)[:1]
            rows.append((attachment.create_date, {
                'document_type': doc_type,
                'name': attachment.name,
                'source_model': self._attachment_source_label(attachment),
                'issue_date': attachment.create_date,
                'attachment_id': attachment.id,
                'service_request_id': request.id if request else False,
                'period_id': period.id if period else False,
                'company_id': doctor.company_id.id or self.env.company.id,
            }))

        rows = sorted(rows, key=lambda item: item[0] or fields.Datetime.now(), reverse=True)
        return [(0, 0, values) for _date, values in rows]

    def _guess_document_type(self, text):
        text = (text or '').lower()
        if any(token in text for token in ('شهادة عضوية', 'membership certificate', 'certificate')):
            return _('شهادة عضوية')
        if any(token in text for token in ('براءة', 'ذمة', 'good standing')):
            return _('براءة ذمة')
        if any(token in text for token in ('بدل فاقد', 'replacement', 'card replacement')):
            return _('بدل فاقد')
        if any(token in text for token in ('وثيقة', 'document', 'authentication')):
            return _('وثيقة')
        return False

    def _get_doctor_document_attachments(self, doctor, service_requests, periods):
        Attachment = self.env['ir.attachment']
        try:
            Attachment.check_access_rights('read')
            domain = [
                '|', '|',
                '&', ('res_model', '=', 'res.partner'), ('res_id', '=', doctor.id),
                '&', ('res_model', '=', 'membership.service.request'), ('res_id', 'in', service_requests.ids or [0]),
                '&', ('res_model', '=', 'membership.period'), ('res_id', 'in', periods.ids or [0]),
            ]
            attachments = Attachment.search(domain, order='create_date desc, id desc')
            linked_attachments = service_requests.mapped('attachment_ids')
            return (attachments | linked_attachments).filtered(lambda attachment: self._guess_document_type(attachment.name or ''))
        except AccessError:
            return Attachment

    def _attachment_source_label(self, attachment):
        labels = {
            'res.partner': _('ملف الطبيب'),
            'membership.service.request': _('طلب خدمة'),
            'membership.period': _('عضوية'),
        }
        return labels.get(attachment.res_model) or _('مرفق')

    def _add_timeline_event(self, events, event_date, request, event_type, title, summary, invoice=False):
        if not event_date:
            return
        events.append((event_date, {
            'event_date': event_date,
            'event_type': event_type,
            'title': title,
            'summary': summary,
            'service_request_id': request.id,
            'invoice_id': invoice.id if invoice else False,
            'state': request.state,
        }))

    def _request_summary(self, request):
        dated_events = [
            (request.cancelled_date, _('تم إلغاء الطلب')),
            (request.completed_date, _('تم إنهاء الخدمة')),
            (request.started_date, _('بدأ تنفيذ الخدمة')),
            (request.paid_date, _('تم تسجيل الدفع')),
            (request.financial_approved_date, _('تم اعتماد الطلب مالياً')),
            (request.submitted_date, _('تم إرساله إلى المالية')),
            (request.create_date, _('تم إنشاء الطلب')),
        ]
        dated_events = [(date, label) for date, label in dated_events if date]
        if dated_events:
            return max(dated_events, key=lambda item: item[0])[1]
        message = request.message_ids[:1]
        if message:
            summary = re.sub('<[^<]+?>', ' ', message.body or '').strip()
            summary = ' '.join(summary.split())
            if summary:
                return summary[:180]
        return dict(request._fields['state'].selection).get(request.state) or _('تحديث على الطلب')

    def _open_service_requests(self, name, domain):
        self.ensure_one()
        if not self.doctor_id:
            raise UserError(_('يرجى اختيار طبيب أولاً.'))
        action = self.env.ref('membership_management.action_membership_service_request').read()[0]
        action['name'] = name
        action['domain'] = [('partner_id', '=', self.doctor_id.id)] + self._company_domain() + domain
        return action

    def action_open_kpi_open_requests(self):
        return self._open_service_requests(_('طلبات خدمات مفتوحة'), [('state', 'not in', ('completed', 'cancelled'))])

    def action_open_kpi_waiting_finance(self):
        return self._open_service_requests(_('بانتظار المالية'), [('state', '=', 'waiting_financial_approval')])

    def action_open_kpi_waiting_payment(self):
        return self._open_service_requests(_('بانتظار الدفع'), [('state', '=', 'waiting_payment')])

    def action_open_kpi_paid_ready(self):
        return self._open_service_requests(_('مدفوعة جاهزة للتنفيذ'), [('state', '=', 'paid')])

    def action_open_kpi_completed(self):
        return self._open_service_requests(_('طلبات منجزة'), [('state', '=', 'completed')])

    def action_open_kpi_unpaid_invoices(self):
        return self.action_open_invoices(extra_domain=[('payment_state', 'in', ('not_paid', 'partial', 'in_payment')), ('amount_residual', '>', 0)])

    def action_open_kpi_residual_invoices(self):
        return self.action_open_kpi_unpaid_invoices()

    def action_create_service_request(self):
        self.ensure_one()
        if not self.doctor_id:
            raise UserError(_('يرجى اختيار طبيب أولاً.'))
        action = self.env.ref('membership_management.action_membership_service_request').read()[0]
        action.update({
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_partner_id': self.doctor_id.id,
                'default_company_id': self.doctor_id.company_id.id or self.env.company.id,
            },
        })
        return action

    def action_new_membership_request(self):
        return self.action_create_service_request()

    def action_renew_membership_request(self):
        return self.action_create_service_request()

    def action_follow_current_request(self):
        self.ensure_one()
        if not self.current_open_request_id:
            raise UserError(_('لا يوجد طلب مفتوح حالياً لهذا الطبيب.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('متابعة الطلب الحالي'),
            'res_model': 'membership.service.request',
            'res_id': self.current_open_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_current_unpaid_invoice(self):
        self.ensure_one()
        if not self.current_unpaid_invoice_id:
            raise UserError(_('لا توجد فاتورة غير مدفوعة لهذا الطبيب.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('الفاتورة غير المدفوعة'),
            'res_model': 'account.move',
            'res_id': self.current_unpaid_invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_doctor(self):
        self.ensure_one()
        if not self.doctor_id:
            raise UserError(_('يرجى اختيار طبيب أولاً.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('نموذج الطبيب'),
            'res_model': 'res.partner',
            'res_id': self.doctor_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_service_requests(self):
        return self._open_service_requests(_('طلبات خدمات الطبيب'), [])

    def action_open_invoices(self, extra_domain=None):
        self.ensure_one()
        if not self.doctor_id:
            raise UserError(_('يرجى اختيار طبيب أولاً.'))
        action = {
            'type': 'ir.actions.act_window',
            'name': _('فواتير الطبيب'),
            'res_model': 'account.move',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [
                ('move_type', '=', 'out_invoice'),
                ('partner_id', '=', self.doctor_id.id),
                ('company_id', 'in', self.env.companies.ids),
            ] + (extra_domain or []),
        }
        return action

    def action_open_memberships(self):
        self.ensure_one()
        if not self.doctor_id:
            raise UserError(_('يرجى اختيار طبيب أولاً.'))
        action = self.env.ref('membership_management.action_membership_period').read()[0]
        action['domain'] = [('partner_id', '=', self.doctor_id.id), ('company_id', 'in', self.env.companies.ids)]
        return action


class MembershipDoctor360ServiceLine(models.TransientModel):
    _name = 'membership.doctor.360.service.line'
    _description = 'سطر طلب خدمة في الملف الموحد للطبيب'

    dashboard_id = fields.Many2one('membership.doctor.360', required=True, ondelete='cascade')
    service_request_id = fields.Many2one('membership.service.request', string='رقم الطلب', readonly=True)
    service_type_id = fields.Many2one('membership.service.type', string='نوع الخدمة', readonly=True)
    state = fields.Selection(related='service_request_id.state', string='الحالة', readonly=True)
    invoice_payment_state = fields.Selection(related='service_request_id.invoice_payment_state', string='حالة الدفع', readonly=True)
    invoice_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    request_create_date = fields.Datetime(string='تاريخ الطلب', readonly=True)
    last_update_date = fields.Datetime(string='آخر تحديث', readonly=True)

    def action_open_service_request(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('طلب خدمة طبيب'), 'res_model': 'membership.service.request', 'res_id': self.service_request_id.id, 'view_mode': 'form', 'target': 'current'}


class MembershipDoctor360PeriodLine(models.TransientModel):
    _name = 'membership.doctor.360.period.line'
    _description = 'سطر عضوية في الملف الموحد للطبيب'

    dashboard_id = fields.Many2one('membership.doctor.360', required=True, ondelete='cascade')
    period_id = fields.Many2one('membership.period', string='العضوية', readonly=True)
    name = fields.Char(string='رقم العضوية', readonly=True)
    subscription_year = fields.Char(string='سنة الاشتراك', readonly=True)
    start_date = fields.Date(string='تاريخ البداية', readonly=True)
    end_date = fields.Date(string='تاريخ النهاية', readonly=True)
    state = fields.Selection(related='period_id.state', string='الحالة', readonly=True)
    invoice_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    payment_state = fields.Selection([
        ('no_invoice', 'لا توجد فاتورة'),
        ('not_paid', 'غير مدفوع'),
        ('in_payment', 'بانتظار التسوية'),
        ('paid', 'مدفوع'),
        ('partial', 'مدفوع جزئياً'),
        ('reversed', 'معكوس'),
        ('blocked', 'محجوب'),
    ], string='حالة الدفع', readonly=True)
    payment_date = fields.Date(string='تاريخ الدفع', readonly=True)

    def action_open_period(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('العضوية'), 'res_model': 'membership.period', 'res_id': self.period_id.id, 'view_mode': 'form', 'target': 'current'}


class MembershipDoctor360InvoiceLine(models.TransientModel):
    _name = 'membership.doctor.360.invoice.line'
    _description = 'سطر فاتورة في الملف الموحد للطبيب'

    dashboard_id = fields.Many2one('membership.doctor.360', required=True, ondelete='cascade')
    invoice_id = fields.Many2one('account.move', string='رقم الفاتورة', readonly=True)
    invoice_date = fields.Date(string='التاريخ', readonly=True)
    origin = fields.Char(string='المصدر', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='طلب الخدمة', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    amount_total = fields.Monetary(string='المبلغ الإجمالي', currency_field='currency_id', readonly=True)
    amount_residual = fields.Monetary(string='المتبقي', currency_field='currency_id', readonly=True)
    payment_state = fields.Selection(related='invoice_id.payment_state', string='حالة الدفع', readonly=True)

    def action_open_invoice(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('الفاتورة'), 'res_model': 'account.move', 'res_id': self.invoice_id.id, 'view_mode': 'form', 'target': 'current'}


class MembershipDoctor360PaymentLine(models.TransientModel):
    _name = 'membership.doctor.360.payment.line'
    _description = 'سطر دفع في الملف الموحد للطبيب'

    dashboard_id = fields.Many2one('membership.doctor.360', required=True, ondelete='cascade')
    payment_id = fields.Many2one('account.payment', string='رقم عملية الدفع', readonly=True)
    payment_date = fields.Date(string='التاريخ', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    amount = fields.Monetary(string='المبلغ', currency_field='currency_id', readonly=True)
    journal_id = fields.Many2one('account.journal', string='دفتر اليومية', readonly=True)
    invoice_names = fields.Char(string='الفاتورة المرتبطة', readonly=True)

    def action_open_payment(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': _('عملية الدفع'), 'res_model': 'account.payment', 'res_id': self.payment_id.id, 'view_mode': 'form', 'target': 'current'}


class MembershipDoctor360ActivityLine(models.TransientModel):
    _name = 'membership.doctor.360.activity.line'
    _description = 'سطر نشاط في الملف الموحد للطبيب'

    dashboard_id = fields.Many2one('membership.doctor.360', required=True, ondelete='cascade')
    activity_date = fields.Datetime(string='التاريخ', readonly=True)
    source_label = fields.Char(string='المصدر', readonly=True)
    summary = fields.Char(string='الوصف', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='طلب الخدمة', readonly=True)
    invoice_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    period_id = fields.Many2one('membership.period', string='العضوية', readonly=True)


class MembershipDoctor360TimelineLine(models.TransientModel):
    _name = 'membership.doctor.360.timeline.line'
    _description = 'سطر المسار الزمني في الملف الموحد للطبيب'
    _order = 'event_date asc, id asc'

    dashboard_id = fields.Many2one('membership.doctor.360', required=True, ondelete='cascade')
    event_date = fields.Datetime(string='التاريخ والوقت', readonly=True)
    event_type = fields.Selection([
        ('created', 'إنشاء الطلب'),
        ('submitted', 'إرساله للمالية'),
        ('finance_approved', 'اعتماد المالية'),
        ('invoice_created', 'إنشاء الفاتورة'),
        ('payment_registered', 'تسجيل القبض'),
        ('service_started', 'بدء التنفيذ'),
        ('service_completed', 'إنهاء الخدمة'),
    ], string='الحدث', readonly=True)
    title = fields.Char(string='المرحلة', readonly=True)
    summary = fields.Char(string='الوصف', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='طلب الخدمة', readonly=True)
    invoice_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    state = fields.Selection(related='service_request_id.state', string='حالة الطلب الحالية', readonly=True)

    def action_open_service_request(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلب خدمة طبيب'),
            'res_model': 'membership.service.request',
            'res_id': self.service_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('لا توجد فاتورة مرتبطة بهذا الحدث.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('الفاتورة'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class MembershipDoctor360DocumentLine(models.TransientModel):
    _name = 'membership.doctor.360.document.line'
    _description = 'سطر وثيقة في الملف الموحد للطبيب'
    _order = 'issue_date desc, id desc'

    dashboard_id = fields.Many2one('membership.doctor.360', required=True, ondelete='cascade')
    document_type = fields.Char(string='نوع الوثيقة', readonly=True)
    name = fields.Char(string='الوثيقة', readonly=True)
    source_model = fields.Char(string='المصدر', readonly=True)
    issue_date = fields.Datetime(string='تاريخ الإصدار', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='طلب الخدمة', readonly=True)
    period_id = fields.Many2one('membership.period', string='العضوية', readonly=True)
    attachment_id = fields.Many2one('ir.attachment', string='المرفق', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

    def action_open_service_request(self):
        self.ensure_one()
        if not self.service_request_id:
            raise UserError(_('لا يوجد طلب خدمة مرتبط بهذه الوثيقة.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلب خدمة طبيب'),
            'res_model': 'membership.service.request',
            'res_id': self.service_request_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_period(self):
        self.ensure_one()
        if not self.period_id:
            raise UserError(_('لا توجد عضوية مرتبطة بهذه الوثيقة.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('العضوية'),
            'res_model': 'membership.period',
            'res_id': self.period_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_attachment(self):
        self.ensure_one()
        if not self.attachment_id:
            raise UserError(_('لا يوجد مرفق مرتبط بهذه الوثيقة.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('الوثيقة'),
            'res_model': 'ir.attachment',
            'res_id': self.attachment_id.id,
            'view_mode': 'form',
            'target': 'current',
        }
