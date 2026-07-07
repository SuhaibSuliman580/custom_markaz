from datetime import datetime, time, timedelta
import re

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MembershipRegistrationWorkspace(models.TransientModel):
    _name = 'membership.registration.workspace'
    _description = 'مركز عمل الذاتية'
    _rec_name = 'name'

    name = fields.Char(string='العنوان', default='مركز عمل الذاتية', readonly=True)
    search_text = fields.Char(string='بحث سريع')
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)

    new_today_count = fields.Integer(string='طلبات جديدة اليوم', readonly=True)
    waiting_finance_count = fields.Integer(string='بانتظار المالية', readonly=True)
    waiting_payment_count = fields.Integer(string='بانتظار الدفع', readonly=True)
    paid_ready_count = fields.Integer(string='مدفوعة جاهزة للتنفيذ', readonly=True)
    in_progress_count = fields.Integer(string='قيد التنفيذ', readonly=True)
    completed_today_count = fields.Integer(string='منجزة اليوم', readonly=True)
    cancelled_today_count = fields.Integer(string='ملغاة اليوم', readonly=True)
    ready_delivery_count = fields.Integer(string='جاهزة للتسليم', readonly=True)
    my_completed_today_count = fields.Integer(string='أنجزتها اليوم', readonly=True)
    my_in_progress_count = fields.Integer(string='قيد التنفيذ لدي', readonly=True)
    my_remaining_task_count = fields.Integer(string='مهامي المتبقية', readonly=True)
    last_served_partner_id = fields.Many2one('res.partner', string='آخر طبيب تمت خدمته', readonly=True)
    has_last_served_doctor = fields.Boolean(string='يوجد آخر طبيب تمت خدمته', readonly=True)

    alert_line_ids = fields.One2many(
        'membership.registration.workspace.alert',
        'workspace_id',
        string='تنبيهات مهمة',
        readonly=True,
    )
    inbox_line_ids = fields.One2many(
        'membership.registration.workspace.line',
        'workspace_id',
        string='مهامي الحالية',
        readonly=True,
    )
    activity_line_ids = fields.One2many(
        'membership.registration.workspace.activity',
        'workspace_id',
        string='آخر النشاطات',
        readonly=True,
    )
    has_alert_lines = fields.Boolean(string='توجد تنبيهات', readonly=True)
    has_inbox_lines = fields.Boolean(string='توجد مهام حالية', readonly=True)
    has_activity_lines = fields.Boolean(string='توجد نشاطات', readonly=True)

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        vals.update({'name': _('مركز عمل الذاتية')})
        vals.update(self._prepare_workspace_values())
        return vals

    @api.model
    def action_open_workspace(self):
        vals = {'name': _('مركز عمل الذاتية')}
        vals.update(self._prepare_workspace_values())
        workspace = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('مركز عمل الذاتية'),
            'res_model': 'membership.registration.workspace',
            'res_id': workspace.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'membership_management.view_membership_registration_workspace_form'
            ).id,
            'target': 'current',
        }

    @api.model
    def _get_today_bounds_utc(self):
        today = fields.Date.context_today(self)
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        start_local = user_tz.localize(datetime.combine(today, time.min))
        stop_local = user_tz.localize(datetime.combine(today + timedelta(days=1), time.min))
        return (
            start_local.astimezone(pytz.UTC).replace(tzinfo=None),
            stop_local.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    @api.model
    def _service_request_company_domain(self):
        return [('company_id', 'in', self.env.companies.ids)]

    @api.model
    def _service_request_action(self, name, domain):
        action = self.env.ref('membership_management.action_membership_service_request').read()[0]
        action['name'] = name
        action['domain'] = self._service_request_company_domain() + domain
        return action

    @api.model
    def _doctor_company_domain(self):
        return [
            ('is_doctor', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
        ]

    @api.model
    def _doctor_search_domain(self, search_text):
        return [
            '&',
            '&',
            ('is_doctor', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', 'in', self.env.companies.ids),
            '|', '|', '|',
            ('name', 'ilike', search_text),
            ('membership_number', 'ilike', search_text),
            ('phone', 'ilike', search_text),
            ('mobile', 'ilike', search_text),
        ]

    @api.model
    def _get_action_required_label(self, request):
        if request.state == 'draft':
            return _('إرسال إلى المالية')
        if request.state == 'paid':
            return _('بدء تنفيذ الخدمة')
        if request.state == 'in_progress':
            return _('إنهاء الخدمة')
        if request.state == 'cancelled' and request.cancel_reason:
            return _('مراجعة الطلب الملغى')
        return _('لا يوجد إجراء')

    @api.model
    def _get_last_message_summary(self, request):
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
        if not message:
            return dict(request._fields['state'].selection).get(request.state) or _('تحديث على الطلب')
        summary = re.sub('<[^<]+?>', ' ', message.body or '').strip()
        summary = ' '.join(summary.split())
        if not summary:
            return message.subject or _('تحديث على الطلب')
        return summary[:180]

    @api.model
    def _prepare_alert_commands(self, company_domain, now_utc):
        Request = self.env['membership.service.request']
        alert_specs = [
            {
                'alert_type': 'ready_execution',
                'level': 'success',
                'title': _('طلبات مدفوعة لم يبدأ تنفيذها'),
                'message': _('توجد طلبات مدفوعة وجاهزة لبدء تنفيذ الخدمة.'),
                'domain': [('state', '=', 'paid')],
            },
            {
                'alert_type': 'long_in_progress',
                'level': 'warning',
                'title': _('طلبات قيد التنفيذ منذ مدة طويلة'),
                'message': _('توجد طلبات قيد التنفيذ منذ أكثر من يومين وتحتاج متابعة.'),
                'domain': [
                    ('state', '=', 'in_progress'),
                    ('started_date', '<=', now_utc - timedelta(days=2)),
                ],
            },
            {
                'alert_type': 'late_finance',
                'level': 'warning',
                'title': _('طلبات بانتظار المالية منذ مدة طويلة'),
                'message': _('توجد طلبات بانتظار تصديق المالية منذ أكثر من يومين.'),
                'domain': [
                    ('state', '=', 'waiting_financial_approval'),
                    ('submitted_date', '<=', now_utc - timedelta(days=2)),
                ],
            },
            {
                'alert_type': 'cancelled_review',
                'level': 'danger',
                'title': _('طلبات ملغاة أو مرفوضة تحتاج مراجعة'),
                'message': _('توجد طلبات ملغاة أو مرفوضة ولها سبب مسجل يحتاج مراجعة الذاتية.'),
                'domain': [
                    ('state', '=', 'cancelled'),
                    ('cancel_reason', '!=', False),
                ],
            },
        ]
        commands = []
        for spec in alert_specs:
            requests = Request.search(company_domain + spec['domain'], order='write_date desc', limit=5)
            count = Request.search_count(company_domain + spec['domain'])
            if not count:
                continue
            commands.append((0, 0, {
                'level': spec['level'],
                'alert_type': spec['alert_type'],
                'action_label': self._get_alert_action_label(spec['alert_type']),
                'title': spec['title'],
                'message': spec['message'],
                'request_count': count,
                'sample_request_ids': [(6, 0, requests.ids)],
            }))
        return commands

    @api.model
    def _get_alert_action_label(self, alert_type):
        labels = {
            'ready_execution': _('عرض الطلبات الجاهزة للتنفيذ'),
            'late_finance': _('عرض الطلبات المتأخرة في المالية'),
            'long_in_progress': _('عرض الطلبات قيد التنفيذ'),
            'cancelled_review': _('عرض الطلبات الملغاة'),
        }
        return labels.get(alert_type) or _('عرض الطلبات')

    @api.model
    def _prepare_workspace_values(self):
        Request = self.env['membership.service.request']
        company_domain = self._service_request_company_domain()
        start_utc, stop_utc = self._get_today_bounds_utc()
        now_utc = fields.Datetime.now()

        def count(extra_domain):
            return Request.search_count(company_domain + extra_domain)

        inbox_requests = Request.search(
            company_domain + [
                '|',
                ('state', 'in', ('draft', 'paid', 'in_progress')),
                '&',
                ('state', '=', 'cancelled'),
                ('cancel_reason', '!=', False),
            ],
            order='write_date desc, create_date desc, id desc',
            limit=80,
        )
        inbox_commands = [
            (0, 0, {
                'service_request_id': request.id,
                'action_required': self._get_action_required_label(request),
                'partner_id': request.partner_id.id,
                'service_type_id': request.service_type_id.id,
                'state': request.state,
                'invoice_payment_state': request.invoice_payment_state,
                'request_create_date': request.create_date,
                'last_update_date': request.write_date,
                'company_id': request.company_id.id,
            })
            for request in inbox_requests
        ]

        today_activity_requests = Request.search(
            company_domain + [
                ('write_date', '>=', start_utc),
                ('write_date', '<', stop_utc),
            ],
            order='write_date desc, id desc',
            limit=10,
        )
        activity_commands = [
            (0, 0, {
                'service_request_id': request.id,
                'partner_id': request.partner_id.id,
                'state': request.state,
                'last_update_date': request.write_date,
                'summary': self._get_last_message_summary(request),
                'company_id': request.company_id.id,
            })
            for request in today_activity_requests
        ]

        alert_commands = self._prepare_alert_commands(company_domain, now_utc)
        last_served_request = Request.search(
            company_domain + [
                ('state', '=', 'completed'),
                ('completed_by_id', '=', self.env.user.id),
                ('completed_date', '>=', start_utc),
                ('completed_date', '<', stop_utc),
            ],
            order='completed_date desc, id desc',
            limit=1,
        )

        return {
            'currency_id': self.env.company.currency_id.id,
            'new_today_count': count([
                ('create_date', '>=', start_utc),
                ('create_date', '<', stop_utc),
            ]),
            'waiting_finance_count': count([('state', '=', 'waiting_financial_approval')]),
            'waiting_payment_count': count([('state', '=', 'waiting_payment')]),
            'paid_ready_count': count([('state', '=', 'paid')]),
            'in_progress_count': count([('state', '=', 'in_progress')]),
            'completed_today_count': count([
                ('state', '=', 'completed'),
                ('completed_date', '>=', start_utc),
                ('completed_date', '<', stop_utc),
            ]),
            'cancelled_today_count': count([
                ('state', '=', 'cancelled'),
                ('cancelled_date', '>=', start_utc),
                ('cancelled_date', '<', stop_utc),
            ]),
            'ready_delivery_count': count([('state', '=', 'completed')]),
            'my_completed_today_count': count([
                ('state', '=', 'completed'),
                ('completed_by_id', '=', self.env.user.id),
                ('completed_date', '>=', start_utc),
                ('completed_date', '<', stop_utc),
            ]),
            'my_in_progress_count': count([
                ('state', '=', 'in_progress'),
                ('started_by_id', '=', self.env.user.id),
            ]),
            'my_remaining_task_count': len(inbox_commands),
            'last_served_partner_id': last_served_request.partner_id.id if last_served_request else False,
            'has_last_served_doctor': bool(last_served_request),
            'has_alert_lines': bool(alert_commands),
            'has_inbox_lines': bool(inbox_commands),
            'has_activity_lines': bool(activity_commands),
            'alert_line_ids': alert_commands,
            'inbox_line_ids': inbox_commands,
            'activity_line_ids': activity_commands,
        }

    def action_refresh_workspace(self):
        for workspace in self:
            vals = workspace._prepare_workspace_values()
            vals['alert_line_ids'] = [(5, 0, 0)] + vals.get('alert_line_ids', [])
            vals['inbox_line_ids'] = [(5, 0, 0)] + vals.get('inbox_line_ids', [])
            vals['activity_line_ids'] = [(5, 0, 0)] + vals.get('activity_line_ids', [])
            workspace.write(vals)
        return True

    def _open_kpi(self, name, domain):
        self.ensure_one()
        return self._service_request_action(name, domain)

    def action_open_kpi_new_today(self):
        start_utc, stop_utc = self._get_today_bounds_utc()
        return self._open_kpi(_('طلبات جديدة اليوم'), [
            ('create_date', '>=', start_utc),
            ('create_date', '<', stop_utc),
        ])

    def action_open_kpi_waiting_finance(self):
        return self._open_kpi(_('بانتظار المالية'), [('state', '=', 'waiting_financial_approval')])

    def action_open_kpi_waiting_payment(self):
        return self._open_kpi(_('بانتظار الدفع'), [('state', '=', 'waiting_payment')])

    def action_open_kpi_paid_ready(self):
        return self._open_kpi(_('مدفوعة جاهزة للتنفيذ'), [('state', '=', 'paid')])

    def action_open_kpi_in_progress(self):
        return self._open_kpi(_('قيد التنفيذ'), [('state', '=', 'in_progress')])

    def action_open_kpi_completed_today(self):
        start_utc, stop_utc = self._get_today_bounds_utc()
        return self._open_kpi(_('منجزة اليوم'), [
            ('state', '=', 'completed'),
            ('completed_date', '>=', start_utc),
            ('completed_date', '<', stop_utc),
        ])

    def action_open_kpi_cancelled_today(self):
        start_utc, stop_utc = self._get_today_bounds_utc()
        return self._open_kpi(_('ملغاة اليوم'), [
            ('state', '=', 'cancelled'),
            ('cancelled_date', '>=', start_utc),
            ('cancelled_date', '<', stop_utc),
        ])

    def action_open_kpi_ready_delivery(self):
        return self._open_kpi(_('جاهزة للتسليم'), [('state', '=', 'completed')])

    def action_open_last_served_doctor(self):
        self.ensure_one()
        if not self.last_served_partner_id:
            raise UserError(_('لا يوجد طبيب تمت خدمته اليوم.'))
        return self.env['membership.doctor.360'].action_open_for_doctor(self.last_served_partner_id)

    def action_create_service_request(self):
        action = self.env.ref('membership_management.action_membership_service_request').read()[0]
        action.update({
            'views': [(False, 'form')],
            'view_mode': 'form',
            'target': 'current',
            'context': {
                'default_company_id': self.env.company.id,
            },
        })
        return action

    def action_open_doctors(self):
        action = self.env.ref('membership_management.action_doctor_partners').read()[0]
        action['domain'] = self._doctor_company_domain()
        action['context'] = {
            'default_is_doctor': True,
            'search_default_filter_active_members': 1,
        }
        return action

    def action_search_workspace(self):
        self.ensure_one()
        search_text = (self.search_text or '').strip()
        if not search_text:
            return self.action_open_doctors()

        request_domain = self._service_request_company_domain() + [
            ('name', 'ilike', search_text),
        ]
        requests = self.env['membership.service.request'].search(request_domain, limit=2)
        if len(requests) == 1:
            return {
                'type': 'ir.actions.act_window',
                'name': _('طلب خدمة طبيب'),
                'res_model': 'membership.service.request',
                'res_id': requests.id,
                'view_mode': 'form',
                'target': 'current',
            }
        if len(requests) > 1:
            action = self.env.ref('membership_management.action_membership_service_request').read()[0]
            action['domain'] = request_domain
            return action

        action = self.env.ref('membership_management.action_doctor_partners').read()[0]
        doctor_domain = self._doctor_search_domain(search_text)
        doctors = self.env['res.partner'].search(doctor_domain, limit=2)
        if len(doctors) == 1:
            return self.env['membership.doctor.360'].action_open_for_doctor(doctors)
        if not doctors:
            raise UserError(_('لا توجد نتائج مطابقة للبحث.'))
        action['domain'] = doctor_domain
        action['context'] = {'default_is_doctor': True}
        return action

    def action_open_service_requests(self):
        action = self.env.ref('membership_management.action_membership_service_request').read()[0]
        action['domain'] = self._service_request_company_domain()
        return action

    def action_open_active_memberships(self):
        action = self.env.ref('membership_management.action_membership_period').read()[0]
        action['domain'] = [
            ('state', '=', 'active'),
            ('company_id', 'in', self.env.companies.ids),
        ]
        action['context'] = {
            'search_default_active': 1,
        }
        return action


class MembershipRegistrationWorkspaceAlert(models.TransientModel):
    _name = 'membership.registration.workspace.alert'
    _description = 'تنبيه مركز عمل الذاتية'

    workspace_id = fields.Many2one(
        'membership.registration.workspace',
        required=True,
        ondelete='cascade',
    )
    level = fields.Selection([
        ('success', 'معلومة'),
        ('warning', 'تنبيه'),
        ('danger', 'مهم'),
    ], string='الأهمية', readonly=True)
    alert_type = fields.Selection([
        ('ready_execution', 'طلبات جاهزة للتنفيذ'),
        ('late_finance', 'طلبات متأخرة في المالية'),
        ('long_in_progress', 'طلبات قيد التنفيذ'),
        ('cancelled_review', 'طلبات ملغاة'),
    ], string='نوع التنبيه', readonly=True)
    action_label = fields.Char(string='الإجراء', readonly=True)
    title = fields.Char(string='التنبيه', readonly=True)
    message = fields.Char(string='الوصف', readonly=True)
    request_count = fields.Integer(string='العدد', readonly=True)
    sample_request_ids = fields.Many2many(
        'membership.service.request',
        'mem_reg_ws_alert_req_rel',
        'alert_id',
        'request_id',
        string='طلبات مرتبطة',
        readonly=True,
    )

    def action_open_related_requests(self):
        self.ensure_one()
        now_utc = fields.Datetime.now()
        domain_by_type = {
            'ready_execution': [('state', '=', 'paid')],
            'late_finance': [
                ('state', '=', 'waiting_financial_approval'),
                ('submitted_date', '<=', now_utc - timedelta(days=2)),
            ],
            'long_in_progress': [
                ('state', '=', 'in_progress'),
                ('started_date', '<=', now_utc - timedelta(days=2)),
            ],
            'cancelled_review': [
                ('state', '=', 'cancelled'),
                ('cancel_reason', '!=', False),
            ],
        }
        domain = domain_by_type.get(self.alert_type) or [('id', 'in', self.sample_request_ids.ids)]
        return self.workspace_id._service_request_action(self.action_label or _('عرض الطلبات'), domain)


class MembershipRegistrationWorkspaceLine(models.TransientModel):
    _name = 'membership.registration.workspace.line'
    _description = 'مهمة ذاتية حالية'

    workspace_id = fields.Many2one(
        'membership.registration.workspace',
        required=True,
        ondelete='cascade',
    )
    action_required = fields.Char(string='الإجراء المطلوب', readonly=True)
    service_request_id = fields.Many2one(
        'membership.service.request',
        string='رقم الطلب',
        readonly=True,
    )
    partner_id = fields.Many2one('res.partner', string='الطبيب', readonly=True)
    service_type_id = fields.Many2one('membership.service.type', string='نوع الخدمة', readonly=True)
    state = fields.Selection(
        related='service_request_id.state',
        string='الحالة',
        readonly=True,
    )
    invoice_payment_state = fields.Selection(
        related='service_request_id.invoice_payment_state',
        string='حالة الدفع',
        readonly=True,
    )
    request_create_date = fields.Datetime(string='تاريخ الطلب', readonly=True)
    last_update_date = fields.Datetime(string='آخر تحديث', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

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

    def _refresh_workspace_action(self):
        self.workspace_id.action_refresh_workspace()
        return {
            'type': 'ir.actions.act_window',
            'name': _('مركز عمل الذاتية'),
            'res_model': 'membership.registration.workspace',
            'res_id': self.workspace_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_submit_to_finance(self):
        self.ensure_one()
        self.service_request_id.action_submit_to_finance()
        return self._refresh_workspace_action()

    def action_start_service(self):
        self.ensure_one()
        self.service_request_id.action_start_service()
        return self._refresh_workspace_action()

    def action_complete_service(self):
        self.ensure_one()
        self.service_request_id.action_complete_service()
        return self._refresh_workspace_action()


class MembershipRegistrationWorkspaceActivity(models.TransientModel):
    _name = 'membership.registration.workspace.activity'
    _description = 'نشاط حديث في مركز عمل الذاتية'

    workspace_id = fields.Many2one(
        'membership.registration.workspace',
        required=True,
        ondelete='cascade',
    )
    service_request_id = fields.Many2one(
        'membership.service.request',
        string='رقم الطلب',
        readonly=True,
    )
    partner_id = fields.Many2one('res.partner', string='الطبيب', readonly=True)
    state = fields.Selection(
        related='service_request_id.state',
        string='الحالة الحالية',
        readonly=True,
    )
    last_update_date = fields.Datetime(string='آخر تحديث', readonly=True)
    summary = fields.Char(string='وصف مختصر', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

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
