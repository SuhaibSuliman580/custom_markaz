from odoo import api, fields, models, _
from odoo.tools.misc import format_amount


class MembershipDailyBrief(models.TransientModel):
    _name = 'membership.daily.brief'
    _description = 'تقرير اليوم'

    name = fields.Char(string='العنوان', default='تقرير اليوم', readonly=True)
    report_date = fields.Date(string='تاريخ التقرير', default=fields.Date.context_today, readonly=True)
    company_id = fields.Many2one(
        'res.company', string='النقابة الفرعية',
        domain=lambda s: [('id', 'in', s.env.companies.ids)])
    scope_label = fields.Char(string='نطاق التقرير', readonly=True)
    show_company_filter = fields.Boolean(string='إظهار فلتر النقابة', compute='_compute_show_company_filter')
    currency_id = fields.Many2one('res.currency', string='العملة', readonly=True)
    completed_today = fields.Integer(string='المعاملات المنجزة اليوم', readonly=True)
    created_today = fields.Integer(string='المعاملات المنشأة اليوم', readonly=True)
    delayed_count = fields.Integer(string='المعاملات المتأخرة حاليًا', readonly=True)
    new_applications = fields.Integer(string='طلبات الانتساب الجديدة', readonly=True)
    renewals = fields.Integer(string='طلبات التجديد', readonly=True)
    new_doctors = fields.Integer(string='الأطباء الجدد اليوم', readonly=True)
    invoice_today_amount = fields.Monetary(
        string='قيمة فواتير الخدمات الصادرة اليوم', currency_field='currency_id', readonly=True)
    issued_service_invoice_amount = fields.Monetary(
        string='إجمالي فواتير الخدمات الصادرة اليوم',
        currency_field='currency_id', readonly=True)
    recognized_revenue_amount = fields.Monetary(
        string='الإيراد المحاسبي المعترف به اليوم',
        currency_field='currency_id', readonly=True)
    has_recognized_revenue = fields.Boolean(
        string='يتوفر مصدر واضح للإيراد المحاسبي', readonly=True)
    collected_amount = fields.Monetary(
        string='المقبوضات المسجلة اليوم', currency_field='currency_id', readonly=True)
    receipts_today = fields.Monetary(string='قيمة المقبوضات اليوم', currency_field='currency_id', readonly=True)
    revenue_today = fields.Monetary(string='إيرادات اليوم', currency_field='currency_id', readonly=True)
    draft_moves = fields.Integer(string='القيود المسودة المتقادمة', readonly=True)
    distribution_issues = fields.Integer(string='مشكلات التوزيع', readonly=True)
    due_tasks = fields.Integer(string='المهام المستحقة اليوم', readonly=True)
    overdue_tasks = fields.Integer(string='المهام المتأخرة', readonly=True)
    top_risk_count = fields.Integer(string='أهم المخاطر', readonly=True)
    top_decision_count = fields.Integer(string='أهم القرارات', readonly=True)
    cash_reconciliation_message = fields.Char(
        default='لا تتوفر بيانات مطابقة الصندوق ضمن هذا المركز.', readonly=True)
    summary = fields.Html(readonly=True, sanitize=True)

    @api.depends_context('allowed_company_ids')
    def _compute_show_company_filter(self):
        show = len(self.env.companies) > 1
        for record in self:
            record.show_company_filter = show

    @api.model
    def action_open_brief(self):
        brief = self.create({'report_date': fields.Date.context_today(self)})
        brief.action_refresh()
        return {'type': 'ir.actions.act_window', 'name': _('تقرير اليوم'), 'res_model': self._name,
                'res_id': brief.id, 'view_mode': 'form', 'target': 'current'}

    def _build_daily_summary(self, m, top_priority=False):
        problems, positives = [], []
        if m['request_delayed_count']:
            problems.append(_('توجد %s معاملات متأخرة تحتاج متابعة.') % m['request_delayed_count'])
        if m['distribution_issue_count']:
            problems.append(_('توجد %s مشكلات في توزيع الإيرادات.') % m['distribution_issue_count'])
        if m['overdue_task_count']:
            problems.append(_('توجد %s مهام متأخرة.') % m['overdue_task_count'])
        if m['completed_today_count']:
            positives.append(_('تم إنجاز %s معاملة اليوم.') % m['completed_today_count'])
        if m['request_created_period_count']:
            positives.append(_('تم إنشاء %s معاملة جديدة.') % m['request_created_period_count'])
        currency = self.env['res.currency'].browse(m['currency_id'])
        invoice_amount = m.get('invoice_today_amount') or 0.0
        receipt_amount = m.get('receipts_today') or 0.0
        if invoice_amount and not receipt_amount:
            positives.append(_('تم إصدار فواتير خدمات اليوم بقيمة %s، ولم تسجل مقبوضات حتى الآن.') % (
                format_amount(self.env, invoice_amount, currency)))
        elif invoice_amount:
            positives.append(_('تم إصدار فواتير خدمات اليوم بقيمة %s.') % (
                format_amount(self.env, invoice_amount, currency)))
        if receipt_amount:
            positives.append(_('سُجلت مقبوضات اليوم بقيمة %s.') % (
                format_amount(self.env, receipt_amount, currency)))
        if m.get('new_doctor_count'):
            positives.append(_('تمت إضافة %s من ملفات الأطباء الجدد اليوم.') % m['new_doctor_count'])
        if not m['distribution_issue_count']:
            positives.append(_('لا توجد مشكلات توزيع إيرادات مسجلة.'))
        if top_priority:
            problems.append(_('أهم إجراء عملي اليوم: %s') % top_priority)
        lines = problems + positives
        if not lines:
            lines = [_('لا توجد حركة كافية لبناء ملخص يومي.')]
        return '<h3>%s</h3><ul>%s</ul>' % (
            _('تقرير اليوم – %s') % fields.Date.to_string(self.report_date),
            ''.join('<li>%s</li>' % line for line in lines))

    def action_refresh(self):
        self.ensure_one()
        m = self.env['membership.executive.metrics.service']._get_executive_metrics(
            self.company_id.id, self.report_date, self.report_date)
        decision_center = self.env['membership.decision.center'].create({
            'company_id': self.company_id.id, 'date_from': self.report_date, 'date_to': self.report_date})
        decisions = decision_center._generate_decisions(m)
        risk_center = self.env['membership.risk.center'].create({
            'company_id': self.company_id.id, 'date_from': self.report_date, 'date_to': self.report_date})
        risks = risk_center._generate_risks(m)
        top = sorted(decisions, key=lambda v: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}[v['priority']])
        self.write({
            'currency_id': m['currency_id'], 'completed_today': m['completed_today_count'],
            'scope_label': (
                self.company_id.display_name if self.company_id
                else _('جميع النقابات المسموحة')),
            'created_today': m['request_created_period_count'], 'delayed_count': m['request_delayed_count'],
            'new_applications': m['new_application_count'], 'renewals': m['renewal_count'],
            'new_doctors': m.get('new_doctor_count', 0),
            'invoice_today_amount': m.get('invoice_today_amount', 0.0),
            'issued_service_invoice_amount': m.get('invoice_today_amount', 0.0),
            # V2 does not currently expose a separately auditable recognition source.
            'recognized_revenue_amount': 0.0,
            'has_recognized_revenue': False,
            'collected_amount': m['receipts_today'],
            'receipts_today': m['receipts_today'], 'revenue_today': m['revenue_today'],
            'draft_moves': m['draft_move_count'], 'distribution_issues': m['distribution_issue_count'],
            'due_tasks': m['due_today_task_count'], 'overdue_tasks': m['overdue_task_count'],
            'top_risk_count': min(5, len(risks)), 'top_decision_count': min(5, len(decisions)),
            'summary': self._build_daily_summary(m, top[0]['suggested_action'] if top else False),
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_command_center(self):
        return self.env['membership.command.center'].action_open_command_center()

    def action_open_decisions(self):
        return self.env['membership.decision.center'].action_open_center()

    def action_open_risks(self):
        return self.env['membership.risk.center'].action_open_center()
