from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class MembershipFinancialWorkspace(models.TransientModel):
    _name = 'membership.financial.workspace'
    _description = 'مركز عمل المالية'
    _inherit = 'membership.workspace.mixin'
    _rec_name = 'name'

    name = fields.Char(string='العنوان', default='مركز عمل المالية', readonly=True)
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)

    waiting_approval_count = fields.Integer(string='طلبات بانتظار الاعتماد', readonly=True)
    waiting_payment_count = fields.Integer(string='طلبات بانتظار الدفع', readonly=True)
    posted_invoice_today_count = fields.Integer(string='فواتير مرحلة اليوم', readonly=True)
    today_fee_total = fields.Monetary(string='إجمالي رسوم اليوم', currency_field='currency_id', readonly=True)
    today_revenue_total = fields.Monetary(string='إجمالي الإيرادات اليوم', currency_field='currency_id', readonly=True)
    rejected_today_count = fields.Integer(string='طلبات مرفوضة اليوم', readonly=True)
    distribution_issue_count = fields.Integer(string='طلبات لديها مشكلة توزيع إيرادات', readonly=True)
    has_pending_work = fields.Boolean(string='توجد أعمال مطلوبة', readonly=True)
    pending_work_summary_html = fields.Html(
        string='الأعمال المطلوبة الآن',
        readonly=True,
        sanitize=False,
    )

    has_alert_lines = fields.Boolean(string='توجد تنبيهات', readonly=True)
    has_inbox_lines = fields.Boolean(string='توجد عناصر وارد', readonly=True)
    has_task_lines = fields.Boolean(string='توجد مهام', readonly=True)
    has_activity_lines = fields.Boolean(string='توجد نشاطات', readonly=True)

    alert_line_ids = fields.One2many(
        'membership.financial.workspace.alert',
        'workspace_id',
        string='التنبيهات المالية',
        readonly=True,
    )
    inbox_line_ids = fields.One2many(
        'membership.financial.workspace.inbox.line',
        'workspace_id',
        string='صندوق الوارد المالي',
        readonly=True,
    )
    task_line_ids = fields.One2many(
        'membership.financial.workspace.task.line',
        'workspace_id',
        string='مهامي الحالية',
        readonly=True,
    )
    activity_line_ids = fields.One2many(
        'membership.financial.workspace.activity.line',
        'workspace_id',
        string='آخر النشاطات',
        readonly=True,
    )

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        vals.update({'name': _('مركز عمل المالية')})
        vals.update(self._prepare_workspace_values())
        return vals

    @api.model
    def action_open_workspace(self):
        vals = {'name': _('مركز عمل المالية')}
        vals.update(self._prepare_workspace_values())
        workspace = self.create(vals)
        return {
            'type': 'ir.actions.act_window',
            'name': _('مركز عمل المالية'),
            'res_model': 'membership.financial.workspace',
            'res_id': workspace.id,
            'view_mode': 'form',
            'view_id': self.env.ref(
                'membership_management.view_membership_financial_workspace_form'
            ).id,
            'target': 'current',
        }

    def action_refresh_workspace(self):
        for workspace in self:
            vals = workspace._prepare_workspace_values()
            vals['alert_line_ids'] = [(5, 0, 0)] + vals.get('alert_line_ids', [])
            vals['inbox_line_ids'] = [(5, 0, 0)] + vals.get('inbox_line_ids', [])
            vals['task_line_ids'] = [(5, 0, 0)] + vals.get('task_line_ids', [])
            vals['activity_line_ids'] = [(5, 0, 0)] + vals.get('activity_line_ids', [])
            workspace.write(vals)
        return True

    def _prepare_workspace_values(self):
        Request = self.env['membership.service.request']
        Invoice = self.env['account.move']
        Ledger = self.env['syndicate.revenue.distribution.ledger.line']
        company_domain = self._workspace_company_domain()
        start_utc, stop_utc = self._workspace_today_bounds_utc()
        today = fields.Date.context_today(self)

        posted_invoice_domain = company_domain + [
            ('move_type', '=', 'out_invoice'),
            ('membership_service_request_id', '!=', False),
            ('state', '=', 'posted'),
            ('invoice_date', '=', today),
        ]
        posted_invoices = Invoice.search(posted_invoice_domain)

        today_ledger_lines = Ledger.search(company_domain + [
            ('state', '=', 'posted'),
            ('invoice_date', '=', today),
        ])
        distribution_issue_count = Request.search_count(company_domain + [
            ('state', '=', 'waiting_financial_approval'),
            ('revenue_distribution_required', '=', True),
            ('revenue_distribution_ready', '=', False),
        ])
        ready_approval_count = Request.search_count(company_domain + [
            ('state', '=', 'waiting_financial_approval'),
            ('financial_validation_ready', '=', True),
        ])
        waiting_approval_count = Request.search_count(company_domain + [
            ('state', '=', 'waiting_financial_approval'),
        ])
        waiting_payment_count = Request.search_count(company_domain + [
            ('state', '=', 'waiting_payment'),
        ])
        rejected_today_count = Request.search_count(company_domain + [
            ('state', '=', 'cancelled'),
            ('cancelled_date', '>=', start_utc),
            ('cancelled_date', '<', stop_utc),
        ])

        alert_commands = self._prepare_alert_commands(company_domain)
        inbox_commands = self._prepare_inbox_commands(company_domain)
        task_commands = self._prepare_task_commands(company_domain)
        activity_commands = self._prepare_activity_commands(company_domain, start_utc, stop_utc)

        return {
            'currency_id': self.env.company.currency_id.id,
            'waiting_approval_count': waiting_approval_count,
            'waiting_payment_count': waiting_payment_count,
            'posted_invoice_today_count': len(posted_invoices),
            'today_fee_total': sum(posted_invoices.mapped('amount_total')),
            'today_revenue_total': sum(today_ledger_lines.mapped('distributed_amount')),
            'rejected_today_count': rejected_today_count,
            'distribution_issue_count': distribution_issue_count,
            'has_pending_work': any([
                waiting_approval_count,
                distribution_issue_count,
                waiting_payment_count,
                rejected_today_count,
            ]),
            'pending_work_summary_html': self._prepare_pending_work_summary_html(
                waiting_approval_count,
                max(waiting_approval_count - ready_approval_count, 0),
                distribution_issue_count,
                waiting_payment_count,
                rejected_today_count,
            ),
            'has_alert_lines': bool(alert_commands),
            'has_inbox_lines': bool(inbox_commands),
            'has_task_lines': bool(task_commands),
            'has_activity_lines': bool(activity_commands),
            'alert_line_ids': alert_commands,
            'inbox_line_ids': inbox_commands,
            'task_line_ids': task_commands,
            'activity_line_ids': activity_commands,
        }

    def _prepare_pending_work_summary_html(
        self,
        waiting_approval_count,
        review_count,
        distribution_issue_count,
        waiting_payment_count,
        rejected_today_count,
    ):
        items = []
        if waiting_approval_count:
            items.append(_('%s طلب بانتظار الاعتماد.') % waiting_approval_count)
        if review_count:
            items.append(_('%s طلب يحتاج مراجعة.') % review_count)
        if distribution_issue_count:
            items.append(_('%s مشكلة توزيع إيرادات.') % distribution_issue_count)
        if waiting_payment_count:
            items.append(_('%s فاتورة بانتظار الدفع.') % waiting_payment_count)
        if rejected_today_count:
            items.append(_('%s طلب مرفوض اليوم.') % rejected_today_count)
        if not items:
            return '<p class="mb-0">لا توجد أعمال مالية معلقة حالياً.</p>'
        return '<p class="mb-2">يوجد:</p><ul class="mb-0">%s</ul>' % ''.join('<li>%s</li>' % item for item in items)

    def _prepare_alert_commands(self, company_domain):
        Request = self.env['membership.service.request']
        Invoice = self.env['account.move']
        FundBox = self.env['syndicate.fund.box']
        DistributionLine = self.env['product.revenue.distribution.line']

        specs = []
        overdue_domain = company_domain + [
            ('state', '=', 'waiting_financial_approval'),
            ('submitted_date', '<=', fields.Datetime.now() - timedelta(days=1)),
        ]
        specs.append({
            'alert_type': 'overdue_finance',
            'level': 'danger',
            'title': _('طلبات بقيت بانتظار المالية أكثر من يوم'),
            'message': _('توجد طلبات تجاوزت حد الانتظار التشغيلي وتحتاج معالجة عاجلة.'),
            'count': Request.search_count(overdue_domain),
            'target_model': 'membership.service.request',
            'domain': overdue_domain,
        })

        bad_distribution_domain = company_domain + [
            ('state', '=', 'waiting_financial_approval'),
            ('revenue_distribution_required', '=', True),
            ('revenue_distribution_ready', '=', False),
        ]
        specs.append({
            'alert_type': 'distribution_not_ready',
            'level': 'danger',
            'title': _('توزيع الإيرادات غير مكتمل'),
            'message': _('توجد طلبات لا يمكن اعتمادها قبل تصحيح إعداد توزيع الإيرادات.'),
            'count': Request.search_count(bad_distribution_domain),
            'target_model': 'membership.service.request',
            'domain': bad_distribution_domain,
        })

        bad_percentage_line_ids = self._get_bad_distribution_percentage_line_ids(company_domain)
        specs.append({
            'alert_type': 'distribution_percentage_not_100',
            'level': 'danger',
            'title': _('نسبة التوزيع لا تساوي 100%'),
            'message': _('توجد منتجات لا يساوي مجموع توزيعها 100% ضمن إحدى الشركات.'),
            'count': len(bad_percentage_line_ids),
            'target_model': 'product.revenue.distribution.line',
            'domain': [('id', 'in', bad_percentage_line_ids)],
        })

        not_ready_domain = company_domain + [
            ('state', '=', 'waiting_financial_approval'),
            ('financial_validation_ready', '=', False),
        ]
        specs.append({
            'alert_type': 'financial_not_ready',
            'level': 'warning',
            'title': _('طلبات تحتاج مراجعة مالية'),
            'message': _('توجد طلبات لم تجتز فحص الجاهزية المالية.'),
            'count': Request.search_count(not_ready_domain),
            'target_model': 'membership.service.request',
            'domain': not_ready_domain,
        })

        missing_invoice_domain = company_domain + [
            ('state', '=', 'waiting_payment'),
            ('invoice_id', '=', False),
        ]
        specs.append({
            'alert_type': 'missing_invoice',
            'level': 'danger',
            'title': _('الفاتورة لم تنشأ'),
            'message': _('توجد طلبات بانتظار الدفع بدون فاتورة مرتبطة.'),
            'count': Request.search_count(missing_invoice_domain),
            'target_model': 'membership.service.request',
            'domain': missing_invoice_domain,
        })

        draft_invoice_domain = company_domain + [
            ('move_type', '=', 'out_invoice'),
            ('membership_service_request_id', '!=', False),
            ('state', '!=', 'posted'),
        ]
        specs.append({
            'alert_type': 'invoice_not_posted',
            'level': 'warning',
            'title': _('الفاتورة غير مرحلة'),
            'message': _('توجد فواتير خدمات أطباء مرتبطة بطلبات ولم ترحل بعد.'),
            'count': Invoice.search_count(draft_invoice_domain),
            'target_model': 'account.move',
            'domain': draft_invoice_domain,
        })

        inactive_funds = FundBox.search(company_domain + [('active', '=', False)], limit=1)
        if inactive_funds:
            inactive_fund_count = FundBox.search_count(company_domain + [('active', '=', False)])
            specs.append({
                'alert_type': 'inactive_fund_box',
                'level': 'warning',
                'title': _('صناديق توزيع غير فعالة'),
                'message': _('توجد صناديق توزيع غير فعالة وقد تمنع جاهزية بعض الطلبات.'),
                'count': inactive_fund_count,
                'target_model': 'syndicate.fund.box',
                'domain': company_domain + [('active', '=', False)],
            })

        missing_income_domain = company_domain + [('income_account_id', '=', False)]
        specs.append({
            'alert_type': 'missing_income_account',
            'level': 'danger',
            'title': _('حساب إيراد غير موجود'),
            'message': _('توجد صناديق توزيع بدون حساب إيراد.'),
            'count': FundBox.search_count(missing_income_domain),
            'target_model': 'syndicate.fund.box',
            'domain': missing_income_domain,
        })

        distribution_lines_without_fund = DistributionLine.search(company_domain + [
            ('fund_box_id', '=', False),
        ], limit=1)
        if distribution_lines_without_fund:
            specs.append({
                'alert_type': 'distribution_not_ready',
                'level': 'warning',
                'title': _('توزيع الإيرادات غير مكتمل'),
                'message': _('توجد أسطر توزيع إيرادات بدون صندوق توزيع.'),
                'count': DistributionLine.search_count(company_domain + [('fund_box_id', '=', False)]),
                'target_model': 'product.revenue.distribution.line',
                'domain': company_domain + [('fund_box_id', '=', False)],
            })

        severity_order = {'danger': 0, 'warning': 1, 'info': 2}
        commands = []
        specs = sorted(specs, key=lambda item: (severity_order.get(item['level'], 99), item['title']))
        for spec in specs:
            if not spec['count']:
                continue
            commands.append((0, 0, {
                'alert_type': spec['alert_type'],
                'level': spec['level'],
                'title': spec['title'],
                'message': spec['message'],
                'record_count': spec['count'],
                'target_model': spec['target_model'],
                'domain_text': repr(spec['domain']),
            }))
        return commands

    def _get_bad_distribution_percentage_line_ids(self, company_domain):
        DistributionLine = self.env['product.revenue.distribution.line']
        grouped_lines = DistributionLine.read_group(
            company_domain,
            ['percentage:sum'],
            ['product_tmpl_id', 'company_id'],
            lazy=False,
        )
        bad_domains = []
        for group in grouped_lines:
            if abs(group.get('percentage', 0.0) - 100.0) <= 0.0001:
                continue
            product_tmpl = group.get('product_tmpl_id')
            company = group.get('company_id')
            if not product_tmpl or not company:
                continue
            bad_domains.append([
                ('product_tmpl_id', '=', product_tmpl[0]),
                ('company_id', '=', company[0]),
            ])
        if not bad_domains:
            return []

        bad_lines = DistributionLine
        for domain in bad_domains:
            bad_lines |= DistributionLine.search(domain)
        return bad_lines.ids

    def _prepare_inbox_commands(self, company_domain):
        requests = self.env['membership.service.request'].search(
            company_domain + [
                ('state', '=', 'waiting_financial_approval'),
            ],
            order='submitted_date asc, write_date asc, create_date asc, id asc',
            limit=80,
        )
        commands = []
        for request in requests:
            wait_start = self._get_finance_wait_start(request)
            wait_hours = self._get_wait_hours(wait_start)
            sla_state = self._get_sla_state(wait_hours)
            action_status = self._get_action_status(request, sla_state)
            commands.append((0, 0, {
                'service_request_id': request.id,
                'partner_id': request.partner_id.id,
                'service_type_id': request.service_type_id.id,
                'invoice_id': request.invoice_id.id,
                'state': request.state,
                'invoice_payment_state': request.invoice_payment_state,
                'financial_validation_ready': request.financial_validation_ready,
                'financial_validation_result': request.financial_validation_result,
                'action_status': action_status,
                'distribution_check_result': request.revenue_distribution_status_message,
                'sla_state': sla_state,
                'wait_duration': self._format_wait_duration(wait_start),
                'finance_submitted_date': wait_start,
                'last_update_date': request.write_date,
                'company_id': request.company_id.id,
            }))
        return commands

    def _get_action_status(self, request, sla_state):
        if sla_state == 'overdue':
            return 'overdue'
        if not request.financial_validation_ready:
            return 'review'
        if request.revenue_distribution_required and not request.revenue_distribution_ready:
            return 'review'
        return 'ready'

    def _get_finance_wait_start(self, request):
        return request.submitted_date or request.write_date or request.create_date

    def _get_wait_hours(self, wait_start):
        if not wait_start:
            return 0.0
        return max((fields.Datetime.now() - wait_start).total_seconds() / 3600.0, 0.0)

    def _get_sla_state(self, wait_hours):
        if wait_hours < 2:
            return 'normal'
        if wait_hours <= 24:
            return 'medium'
        return 'overdue'

    def _format_wait_duration(self, wait_start):
        if not wait_start:
            return _('غير معروف')
        minutes = int(max((fields.Datetime.now() - wait_start).total_seconds() // 60, 0))
        if minutes < 60:
            if minutes <= 1:
                return _('منذ دقيقة')
            return _('منذ %s دقائق') % minutes
        hours = minutes // 60
        if hours < 24:
            if hours == 1:
                return _('منذ ساعة')
            if hours == 2:
                return _('منذ ساعتين')
            return _('منذ %s ساعات') % hours
        days = hours // 24
        if days == 1:
            return _('منذ يوم')
        return _('منذ %s أيام') % days

    def _prepare_task_commands(self, company_domain):
        requests = self.env['membership.service.request'].search(
            company_domain + [
                ('state', '=', 'waiting_financial_approval'),
                ('financial_validation_ready', '=', True),
            ],
            order='submitted_date asc, create_date asc, id asc',
            limit=15,
        )
        return [(0, 0, {
            'service_request_id': request.id,
            'partner_id': request.partner_id.id,
            'service_type_id': request.service_type_id.id,
            'task_name': _('اعتماد طلب جاهز'),
            'submitted_date': self._get_finance_wait_start(request),
            'wait_duration': self._format_wait_duration(self._get_finance_wait_start(request)),
            'company_id': request.company_id.id,
        }) for request in requests]

    def _prepare_activity_commands(self, company_domain, start_utc, stop_utc):
        requests = self.env['membership.service.request'].search(
            company_domain + [
                '|', '|',
                '&', ('financial_approved_date', '>=', start_utc), ('financial_approved_date', '<', stop_utc),
                '&', ('cancelled_date', '>=', start_utc), ('cancelled_date', '<', stop_utc),
                '&', ('write_date', '>=', start_utc), ('write_date', '<', stop_utc),
            ],
            order='write_date desc, id desc',
            limit=20,
        )
        commands = []
        for request in requests:
            commands.append((0, 0, {
                'service_request_id': request.id,
                'partner_id': request.partner_id.id,
                'invoice_id': request.invoice_id.id,
                'state': request.state,
                'activity_date': request.write_date,
                'summary': self._get_activity_summary(request),
                'user_id': self._get_activity_user(request).id,
                'company_id': request.company_id.id,
            }))
        return commands

    def _get_activity_summary(self, request):
        if request.financial_approved_date:
            return _('تم اعتماد الطلب مالياً')
        if request.state == 'cancelled':
            return _('تم رفض أو إلغاء الطلب')
        if request.invoice_id:
            return _('تحديث مالي على الطلب أو الفاتورة')
        return _('تحديث على طلب خدمة')

    def _get_activity_user(self, request):
        if request.financial_approved_date and request.financial_approved_by_id:
            return request.financial_approved_by_id
        if request.cancelled_date and request.cancelled_by_id:
            return request.cancelled_by_id
        return request.write_uid

    def _open_kpi(self, name, domain):
        self.ensure_one()
        return self._workspace_service_request_action(name, domain)

    def action_open_kpi_waiting_approval(self):
        return self._open_kpi(_('طلبات بانتظار الاعتماد'), [('state', '=', 'waiting_financial_approval')])

    def action_open_kpi_waiting_payment(self):
        return self._open_kpi(_('طلبات بانتظار الدفع'), [('state', '=', 'waiting_payment')])

    def action_open_kpi_posted_invoices_today(self):
        today = fields.Date.context_today(self)
        return self._workspace_invoice_action(_('فواتير خدمات الأطباء المرحّلة اليوم'), [
            ('state', '=', 'posted'),
            ('invoice_date', '=', today),
        ])

    def action_open_kpi_today_fees(self):
        return self.action_open_kpi_posted_invoices_today()

    def action_open_kpi_today_revenue(self):
        today = fields.Date.context_today(self)
        return self._workspace_revenue_ledger_action(_('إيرادات اليوم'), [
            ('state', '=', 'posted'),
            ('invoice_date', '=', today),
        ])

    def action_open_kpi_rejected_today(self):
        start_utc, stop_utc = self._workspace_today_bounds_utc()
        return self._open_kpi(_('طلبات مرفوضة اليوم'), [
            ('state', '=', 'cancelled'),
            ('cancelled_date', '>=', start_utc),
            ('cancelled_date', '<', stop_utc),
        ])

    def action_open_finance_approval(self):
        return self.env.ref('membership_management.action_membership_service_finance_approval').read()[0]

    def action_open_service_types(self):
        return self.env.ref('membership_management.action_membership_service_type').read()[0]

    def action_open_invoice_templates(self):
        return self.env.ref('odoo_invoice_service_template_17.action_invoice_service_template').read()[0]

    def action_open_fund_boxes(self):
        return self.env.ref('syndicate_revenue_distribution.action_syndicate_fund_box').read()[0]

    def action_open_revenue_products(self):
        return self._workspace_action(
            'product.template',
            _('المنتجات'),
            [],
            context={
                'default_sale_ok': True,
                'default_detailed_type': 'service',
                'default_enable_revenue_distribution': True,
            },
        )

    def action_open_revenue_distribution(self):
        return self.env.ref('syndicate_revenue_distribution.action_revenue_distribution_template').read()[0]

    def action_open_fund_box_templates(self):
        action = self.env.ref('syndicate_revenue_distribution.action_revenue_distribution_template').read()[0]
        action['name'] = _('قوالب الصناديق')
        return action

    def action_open_invoices(self):
        return self._workspace_invoice_action(_('فواتير خدمات الأطباء'))

    def action_open_revenue_reports_placeholder(self):
        return self.env.ref('syndicate_revenue_distribution.action_revenue_distribution_dashboard').read()[0]


class MembershipFinancialWorkspaceAlert(models.TransientModel):
    _name = 'membership.financial.workspace.alert'
    _description = 'تنبيه مركز عمل المالية'

    workspace_id = fields.Many2one('membership.financial.workspace', required=True, ondelete='cascade')
    alert_type = fields.Selection([
        ('distribution_not_ready', 'توزيع الإيرادات غير مكتمل'),
        ('distribution_percentage_not_100', 'نسبة التوزيع لا تساوي 100%'),
        ('financial_not_ready', 'غير جاهز مالياً'),
        ('missing_invoice', 'الفاتورة لم تنشأ'),
        ('invoice_not_posted', 'الفاتورة غير مرحلة'),
        ('inactive_fund_box', 'صندوق غير فعال'),
        ('missing_income_account', 'حساب إيراد غير موجود'),
        ('overdue_finance', 'متأخر في المالية'),
    ], string='نوع التنبيه', readonly=True)
    level = fields.Selection([
        ('info', 'معلومات'),
        ('warning', 'تنبيه'),
        ('danger', 'عاجل'),
    ], string='الأهمية', readonly=True)
    title = fields.Char(string='التنبيه', readonly=True)
    message = fields.Char(string='الوصف', readonly=True)
    record_count = fields.Integer(string='العدد', readonly=True)
    target_model = fields.Char(string='النموذج المستهدف', readonly=True)
    domain_text = fields.Char(string='النطاق', readonly=True)

    def action_open_related_records(self):
        self.ensure_one()
        domain = safe_eval(self.domain_text or '[]')
        return self.workspace_id._workspace_action(self.target_model, self.title, domain)


class MembershipFinancialWorkspaceInboxLine(models.TransientModel):
    _name = 'membership.financial.workspace.inbox.line'
    _description = 'صندوق الوارد المالي'

    workspace_id = fields.Many2one('membership.financial.workspace', required=True, ondelete='cascade')
    action_status = fields.Selection([
        ('ready', 'جاهز للاعتماد'),
        ('review', 'يتطلب مراجعة'),
        ('overdue', 'متأخر'),
    ], string='الأولوية', readonly=True)
    sla_state = fields.Selection([
        ('normal', 'عادي'),
        ('medium', 'متوسط'),
        ('overdue', 'متأخر'),
    ], string='SLA', readonly=True)
    wait_duration = fields.Char(string='مدة الانتظار', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='رقم الطلب', readonly=True)
    partner_id = fields.Many2one('res.partner', string='الطبيب', readonly=True)
    service_type_id = fields.Many2one('membership.service.type', string='نوع الخدمة', readonly=True)
    invoice_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    state = fields.Selection(related='service_request_id.state', string='الحالة', readonly=True)
    invoice_payment_state = fields.Selection(related='service_request_id.invoice_payment_state', string='حالة الدفع', readonly=True)
    financial_validation_ready = fields.Boolean(string='جاهز مالياً', readonly=True)
    financial_validation_result = fields.Char(string='نتيجة الفحص', readonly=True)
    distribution_check_result = fields.Text(string='نتيجة فحص التوزيع', readonly=True)
    finance_submitted_date = fields.Datetime(string='تاريخ الإرسال', readonly=True)
    last_update_date = fields.Datetime(string='آخر تحديث', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

    def _refresh_workspace_action(self):
        workspace = self.workspace_id
        workspace.action_refresh_workspace()
        return {
            'type': 'ir.actions.act_window',
            'name': _('مركز عمل المالية'),
            'res_model': 'membership.financial.workspace',
            'res_id': workspace.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_open_service_request(self):
        self.ensure_one()
        return self.workspace_id._workspace_open_record(
            _('طلب خدمة طبيب'),
            'membership.service.request',
            self.service_request_id,
        )

    def action_open_doctor_360(self):
        self.ensure_one()
        return self.env['membership.doctor.360'].action_open_for_doctor(self.partner_id)

    def action_open_invoice(self):
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('لا توجد فاتورة مرتبطة بهذا الطلب.'))
        return self.workspace_id._workspace_open_record(_('الفاتورة'), 'account.move', self.invoice_id)

    def action_approve_request(self):
        self.ensure_one()
        self.service_request_id.action_approve_financial_request()
        return self._refresh_workspace_action()


class MembershipFinancialWorkspaceTaskLine(models.TransientModel):
    _name = 'membership.financial.workspace.task.line'
    _description = 'مهمة مالية حالية'

    workspace_id = fields.Many2one('membership.financial.workspace', required=True, ondelete='cascade')
    task_name = fields.Char(string='المهمة', readonly=True)
    service_request_id = fields.Many2one('membership.service.request', string='رقم الطلب', readonly=True)
    partner_id = fields.Many2one('res.partner', string='الطبيب', readonly=True)
    service_type_id = fields.Many2one('membership.service.type', string='نوع الخدمة', readonly=True)
    submitted_date = fields.Datetime(string='تاريخ الإرسال', readonly=True)
    wait_duration = fields.Char(string='مدة الانتظار', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

    def action_open_service_request(self):
        self.ensure_one()
        return self.workspace_id._workspace_open_record(
            _('طلب خدمة طبيب'),
            'membership.service.request',
            self.service_request_id,
        )

    def action_approve_request(self):
        self.ensure_one()
        workspace = self.workspace_id
        self.service_request_id.action_approve_financial_request()
        workspace.action_refresh_workspace()
        return {
            'type': 'ir.actions.act_window',
            'name': _('مركز عمل المالية'),
            'res_model': 'membership.financial.workspace',
            'res_id': workspace.id,
            'view_mode': 'form',
            'target': 'current',
        }


class MembershipFinancialWorkspaceActivityLine(models.TransientModel):
    _name = 'membership.financial.workspace.activity.line'
    _description = 'نشاط مالي حديث'

    workspace_id = fields.Many2one('membership.financial.workspace', required=True, ondelete='cascade')
    service_request_id = fields.Many2one('membership.service.request', string='رقم الطلب', readonly=True)
    partner_id = fields.Many2one('res.partner', string='الطبيب', readonly=True)
    invoice_id = fields.Many2one('account.move', string='الفاتورة', readonly=True)
    state = fields.Selection(related='service_request_id.state', string='الحالة', readonly=True)
    activity_date = fields.Datetime(string='التاريخ', readonly=True)
    summary = fields.Char(string='الملخص', readonly=True)
    user_id = fields.Many2one('res.users', string='المستخدم', readonly=True)
    company_id = fields.Many2one('res.company', string='الشركة', readonly=True)

    def action_open_service_request(self):
        self.ensure_one()
        return self.workspace_id._workspace_open_record(
            _('طلب خدمة طبيب'),
            'membership.service.request',
            self.service_request_id,
        )
