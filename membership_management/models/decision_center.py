import json
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError


PRIORITIES = [('critical', 'حرج'), ('high', 'مرتفع'), ('medium', 'متوسط'), ('low', 'منخفض')]
CONFIDENCE = [('high', 'مرتفع'), ('medium', 'متوسط'), ('low', 'منخفض')]


class ExecutiveDecision(models.Model):
    _name = 'membership.executive.decision'
    _description = 'قرار تنفيذي'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'priority_rank, create_date desc'

    name = fields.Char(string='العنوان', required=True, tracking=True)
    scope_type = fields.Selection(
        [('central', 'مركزي'), ('company', 'نقابة فرعية')],
        string='نطاق القرار', required=True, default='company', index=True)
    scope_label = fields.Char(string='وصف النطاق', required=True, default='مركزي')
    company_id = fields.Many2one('res.company', string='النقابة الفرعية', index=True)
    source_rule_code = fields.Char(string='رمز القاعدة', required=True, index=True)
    logical_key = fields.Char(string='مفتاح منع التكرار', required=True, index=True)
    description = fields.Text(string='المشكلة', required=True)
    recommendation = fields.Text(string='التوصية الإدارية', required=True)
    priority = fields.Selection(PRIORITIES, string='الأولوية', required=True, tracking=True)
    priority_rank = fields.Integer(default=30, index=True)
    responsible_user_id = fields.Many2one('res.users', string='المسؤول', tracking=True)
    due_date = fields.Date(string='تاريخ الاستحقاق', tracking=True)
    state = fields.Selection([
        ('proposed', 'مقترح'), ('under_review', 'بانتظار المراجعة'),
        ('accepted', 'معتمد'), ('dismissed', 'مرفوض'), ('completed', 'مكتمل'),
    ], string='الحالة', default='proposed', required=True, tracking=True)
    source_model = fields.Char()
    source_domain = fields.Text()
    related_risk_id = fields.Many2one('membership.executive.risk', string='الخطر المرتبط')
    created_from_center = fields.Boolean(default=True)
    completion_date = fields.Datetime(string='تاريخ الإكمال', readonly=True)
    _sql_constraints = [
        ('logical_key_unique', 'unique(logical_key)', 'يوجد قرار محفوظ لهذا المؤشر والفترة بالفعل.'),
    ]

    def action_complete(self):
        self.write({'state': 'completed', 'completion_date': fields.Datetime.now()})

    @api.constrains('scope_type', 'company_id')
    def _check_company_scope(self):
        for record in self:
            if record.scope_type == 'company' and not record.company_id:
                raise UserError(_('يجب تحديد النقابة الفرعية للقرار الفرعي.'))


class MembershipDecisionCenter(models.TransientModel):
    _name = 'membership.decision.center'
    _description = 'مركز القرارات'
    _inherit = 'membership.workspace.mixin'

    name = fields.Char(default='مركز القرارات', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='النقابة الفرعية',
        domain=lambda s: [('id', 'in', s.env.companies.ids)])
    date_from = fields.Date(string='من تاريخ')
    date_to = fields.Date(string='إلى تاريخ', default=fields.Date.context_today)
    decision_category = fields.Selection([
        ('data', 'البيانات'), ('financial', 'مالي'), ('administrative', 'إداري'),
        ('operational', 'تشغيلي'), ('membership', 'العضوية'), ('fund', 'الصناديق'),
        ('compliance', 'الالتزام'),
    ], string='الفئة')
    priority_filter = fields.Selection(PRIORITIES, string='الأولوية')
    status_filter = fields.Selection([
        ('proposed', 'مقترح'), ('under_review', 'قيد المراجعة'),
        ('accepted', 'معتمد'), ('dismissed', 'مرفوض'), ('completed', 'مكتمل'),
    ], string='الحالة')
    responsible_user_id = fields.Many2one('res.users', string='المسؤول')
    line_ids = fields.One2many('membership.decision.center.line', 'center_id', readonly=True)
    critical_count = fields.Integer(readonly=True)
    high_count = fields.Integer(readonly=True)
    medium_count = fields.Integer(readonly=True)
    review_count = fields.Integer(readonly=True)
    accepted_count = fields.Integer(readonly=True)
    completed_count = fields.Integer(readonly=True)
    proposed_count = fields.Integer(string='قرارات مقترحة', readonly=True)
    under_review_count = fields.Integer(string='بانتظار المراجعة', readonly=True)

    MISSING_SPECIALTY_THRESHOLD = 20.0
    MISSING_NATIONAL_THRESHOLD = 5.0
    DELAYED_REQUEST_THRESHOLD = 5
    COLLECTION_RATE_THRESHOLD = 70.0
    LOW_BRANCH_SCORE = 60.0
    WORKLOAD_THRESHOLD = 20

    @api.model
    def action_open_center(self):
        center = self.create({'date_to': fields.Date.context_today(self)})
        center.action_refresh()
        return {'type': 'ir.actions.act_window', 'name': _('مركز القرارات'),
                'res_model': self._name, 'res_id': center.id, 'view_mode': 'form', 'target': 'current'}

    def _get_decision_rules(self):
        return [
            ('missing_specialty', 'data', 'doctor_missing_specialty', 'doctor_missing_specialty_rate',
             self.MISSING_SPECIALTY_THRESHOLD, _('نقص اختصاصات الأطباء'),
             _('نسبة مرتفعة من ملفات الأطباء دون اختصاص.'),
             _('ضعف جودة الإحصائيات والتقارير حسب الاختصاص.'),
             _('إطلاق حملة تحديث بيانات تستهدف الأطباء ناقصي الاختصاص.')),
            ('missing_national', 'compliance', 'doctor_missing_national_id', 'doctor_missing_national_rate',
             self.MISSING_NATIONAL_THRESHOLD, _('نقص الرقم الوطني'),
             _('ملفات أطباء تفتقد الرقم الوطني.'), _('قد تتأثر دقة الهوية والتقارير والعمليات الانتخابية.'),
             _('تنفيذ حملة تدقيق هوية وربط الاستكمال بالخدمات الجديدة.')),
            ('duplicate_national', 'compliance', 'doctor_duplicate_national_id', 'doctor_duplicate_rate',
             0.0, _('أرقام وطنية مكررة'), _('توجد أرقام وطنية مكررة.'),
             _('قد تنتج ازدواجية في الاستخدام المالي أو الانتخابي.'),
             _('مراجعة السجلات المكررة قبل أي استخدام انتخابي أو مالي.')),
            ('delayed_requests', 'operational', 'request_delayed_count', False,
             self.DELAYED_REQUEST_THRESHOLD, _('معاملات متأخرة'), _('توجد معاملات تجاوزت مهلة الإنجاز.'),
             _('تراكم العمل وتأخر خدمة الأطباء.'), _('مراجعة المعاملات الأقدم وإعادة توزيع عبء العمل.')),
            ('overdue_invoices', 'financial', 'overdue_amount', False, 0.0,
             _('فواتير متأخرة'), _('توجد أرصدة تجاوزت تاريخ الاستحقاق الفعلي.'),
             _('ارتفاع الذمم وتأخر التدفقات النقدية.'),
             _('إرسال كشف بالفواتير المتأخرة للفرع أو المسؤول المالي.')),
            ('low_collection', 'financial', 'unpaid_invoice_total', 'collection_rate',
             0.0, _('ضعف التحصيل'), _('الرصيد غير المحصل مرتفع أو نسبة التحصيل منخفضة.'),
             _('ضغط على السيولة واستمرار الذمم المفتوحة.'), _('إعداد خطة تحصيل ومراجعة أكبر الذمم.')),
            ('draft_moves', 'financial', 'draft_move_count', False, 0.0,
             _('قيود غير مرحلة'), _('توجد قيود محاسبية في حالة المسودة.'),
             _('تعليق الإقفال ودقة العرض المالي.'), _('مراجعة القيود المسودة والأعمال المحاسبية المعلقة.')),
            ('distribution_issues', 'fund', 'distribution_issue_count', False, 0.0,
             _('مشكلات توزيع الإيرادات'), _('توجد حالات توزيع غير مكتملة فعليًا.'),
             _('عدم اكتمال تخصيص الإيرادات للصناديق.'), _('مراجعة الفواتير المرتبطة قبل الإقفال المالي.')),
            ('unassigned_doctors', 'data', 'doctor_unassigned_count', False, 0.0,
             _('أطباء بلا نقابة فرعية'), _('توجد ملفات أطباء غير مرتبطة بشركة.'),
             _('قصور في عزل البيانات وتقارير الفروع.'), _('مراجعة السجلات وربطها بالشركة الصحيحة.')),
            ('unassigned_requests', 'administrative', 'unassigned_request_count', False, 0.0,
             _('معاملات غير مسندة'), _('توجد معاملات مفتوحة بلا مسؤول.'),
             _('احتمال تأخر المعالجة وغياب المساءلة.'), _('تعيين مسؤول لكل معاملة مفتوحة.')),
        ]

    def _priority(self, code, value, percentage):
        if code == 'duplicate_national':
            return 'critical' if value > 20 else ('high' if value >= 5 else 'medium')
        if code == 'missing_specialty':
            return 'high' if percentage > 30 else 'medium'
        if code in ('overdue_invoices', 'distribution_issues'):
            return 'high'
        return 'high' if value >= 20 else 'medium'

    @api.model
    def _priority_due_days(self, priority):
        return {'critical': 2, 'high': 7, 'medium': 14, 'low': 30}[priority]

    @api.model
    def _suggested_action(self, code, value):
        actions = {
            'missing_specialty': _('فتح ملفات الأطباء دون اختصاص وتكليف مدير العضوية ببدء المعالجة.'),
            'missing_national': _('فتح الملفات الناقصة وتعيين مسؤول لاستكمال بيانات الهوية.'),
            'duplicate_national': _('فتح السجلات المكررة وإنشاء مهمة تدقيق قبل الاستخدام.'),
            'delayed_requests': _('فتح المعاملات المتأخرة وترتيبها من الأقدم ثم إعادة إسناد المتعثر منها.'),
            'overdue_invoices': _('فتح الفواتير التي تجاوزت تاريخ الاستحقاق وإسناد متابعة التحصيل.'),
            'low_collection': _('فتح الذمم الأعلى قيمة وإعداد قائمة متابعة تحصيل.'),
            'draft_moves': _('فتح القيود المسودة التي تجاوزت مهلة التقادم ومراجعتها محاسبيًا.'),
            'distribution_issues': _('فتح حالات التوزيع غير المكتملة وتعيين مسؤول للمراجعة.'),
            'unassigned_doctors': _('فتح ملفات الأطباء غير المرتبطة وتدقيق النقابة الفرعية الصحيحة.'),
            'unassigned_requests': _('فتح المعاملات غير المسندة وتعيين مسؤول لكل معاملة.'),
        }
        return actions[code]

    @api.model
    def _scope_values(self, company_id=False):
        if company_id:
            company = self.env['res.company'].browse(company_id)
            return 'company', company.display_name
        return 'central', _('جميع النقابات المسموحة')

    @api.model
    def _responsible_role_for_rule(self, code, category):
        if category in ('data', 'membership', 'compliance'):
            return _('مدير العضوية')
        if category == 'financial':
            return _('المسؤول المالي')
        if category == 'fund':
            return _('مدير المالية')
        if code in ('delayed_requests', 'unassigned_requests'):
            return _('رئيس القسم أو المدير الإداري')
        return _('غير معين')

    @api.model
    def _decision_source_domain(self, code, metrics):
        today = fields.Date.context_today(self)
        domains = {
            'missing_specialty': [('is_doctor', '=', True), ('medical_specialty_id', '=', False)],
            'missing_national': [('is_doctor', '=', True), ('national_id', 'in', (False, ''))],
            'unassigned_doctors': [('is_doctor', '=', True), ('company_id', '=', False)],
            'delayed_requests': [('state', 'not in', ('completed', 'cancelled'))],
            'unassigned_requests': [('state', 'not in', ('completed', 'cancelled')),
                                    ('started_by_id', '=', False), ('submitted_by_id', '=', False)],
            'overdue_invoices': [('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
                                 ('payment_state', 'not in', ('paid', 'reversed')),
                                 ('invoice_date_due', '<', fields.Date.to_string(today))],
            'draft_moves': [('state', '=', 'draft'),
                            ('date', '<', fields.Date.to_string(
                                today - timedelta(days=metrics.get('draft_move_age_days', 7))))],
        }
        return domains.get(code, [])

    def _generate_decisions(self, metrics):
        vals = []
        for rule in self._get_decision_rules():
            code, category, value_key, percentage_key, threshold, title, problem, impact, recommendation = rule
            value = metrics.get(value_key) or 0.0
            percentage = metrics.get(percentage_key, False) if percentage_key else False
            applies = value > threshold if threshold == 0 else (percentage >= threshold if percentage_key else value >= threshold)
            if code == 'low_collection':
                applies = bool(value and metrics.get('collection_rate', 100.0) < self.COLLECTION_RATE_THRESHOLD)
            if not applies or not value:
                continue
            priority = self._priority(code, value, percentage or 0.0)
            generated_date = fields.Date.context_today(self)
            scope_type, scope_label = self._scope_values(self.company_id.id)
            vals.append({
                'company_id': self.company_id.id or False, 'scope_type': scope_type,
                'scope_label': scope_label, 'decision_category': category,
                'title': title, 'problem_description': problem, 'current_value': value,
                'percentage_value': percentage or 0.0, 'has_percentage': percentage is not False,
                'impact_description': impact,
                'recommendation': recommendation, 'suggested_action': self._suggested_action(code, value),
                'priority': priority, 'severity': priority,
                'responsible_role': self._responsible_role_for_rule(code, category),
                'expected_duration': _('%s يومًا') % self._priority_due_days(priority),
                'due_date': generated_date + timedelta(days=self._priority_due_days(priority)),
                'related_model': 'res.partner' if code.startswith(('missing_', 'duplicate_', 'unassigned_doctors')) else
                                 ('account.move' if code in ('overdue_invoices', 'draft_moves') else 'membership.service.request'),
                'related_domain': json.dumps(
                    self._decision_source_domain(code, metrics), ensure_ascii=False), 'sequence': 10,
                'status': 'proposed', 'rule_code': code, 'rule_reason': problem,
                'confidence_level': metrics.get('evaluation_confidence') or 'medium',
            })
        for branch in metrics.get('branch_lines', []):
            if branch.get('has_health_score') and branch.get('branch_health_score', 100) < self.LOW_BRANCH_SCORE:
                company = branch.get('company_id')
                scope_type, scope_label = self._scope_values(company[0] if company else False)
                vals.append({
                    'company_id': company[0] if company else False, 'scope_type': scope_type,
                    'scope_label': scope_label, 'decision_category': 'administrative',
                    'title': _('فرع منخفض الأداء'), 'problem_description': _('درجة صحة الفرع أقل من 60.'),
                    'current_value': branch.get('branch_health_score'), 'has_percentage': False,
                    'impact_description': _('تراجع الأداء التنفيذي للفرع.'),
                    'recommendation': _('طلب خطة تصحيح ومتابعتها أسبوعيًا.'), 'suggested_action': _('فتح مركز قيادة الفرع.'),
                    'priority': 'high', 'severity': 'high', 'responsible_role': _('مدير الفرع'),
                    'expected_duration': _('7 أيام'), 'due_date': fields.Date.context_today(self) + timedelta(days=7),
                    'related_model': 'res.company', 'related_domain': json.dumps([['id', '=', company[0]]]),
                    'sequence': 5, 'status': 'proposed', 'rule_code': 'low_branch',
                    'rule_reason': _('درجة صحة موثوقة ومنخفضة.'), 'confidence_level': branch.get('evaluation_confidence') or 'medium',
                })
        return vals

    def action_refresh(self):
        self.ensure_one()
        current = {
            (line.rule_code, line.scope_type, line.company_id.id or 0): {
                'status': line.status, 'due_date': line.due_date,
                'responsible_user_id': line.responsible_user_id.id,
            }
            for line in self.line_ids
        }
        metrics = self.env['membership.executive.metrics.service']._get_executive_metrics(
            self.company_id.id, self.date_from, self.date_to)
        values = self._generate_decisions(metrics)
        period = '%s:%s' % (self.date_from or '', self.date_to or '')
        logical_keys = {
            '%s:%s:%s:%s' % (
                value['rule_code'], value['scope_type'],
                value.get('company_id') or 0, period): value
            for value in values
        }
        persisted = self.env['membership.executive.decision'].search(
            [('logical_key', 'in', list(logical_keys))]) if logical_keys else self.env['membership.executive.decision']
        persisted_by_key = {record.logical_key: record for record in persisted}
        for key, value in logical_keys.items():
            local = current.get((
                value['rule_code'], value['scope_type'], value.get('company_id') or 0))
            if local:
                value.update({field: local[field] for field in (
                    'status', 'due_date', 'responsible_user_id') if local.get(field)})
            saved = persisted_by_key.get(key)
            if saved:
                value.update({
                    'status': saved.state, 'due_date': saved.due_date,
                    'responsible_user_id': saved.responsible_user_id.id,
                })
        if self.decision_category:
            values = [v for v in values if v['decision_category'] == self.decision_category]
        if self.priority_filter:
            values = [v for v in values if v['priority'] == self.priority_filter]
        self.line_ids = [(5, 0, 0)] + [(0, 0, value) for value in values]
        self.write({
            'critical_count': sum(v['priority'] == 'critical' for v in values),
            'high_count': sum(v['priority'] == 'high' for v in values),
            'medium_count': sum(v['priority'] == 'medium' for v in values),
            'review_count': sum(v['status'] == 'under_review' for v in values),
            'proposed_count': sum(v['status'] == 'proposed' for v in values),
            'under_review_count': sum(v['status'] == 'under_review' for v in values),
            'accepted_count': sum(v['status'] == 'accepted' for v in values),
            'completed_count': sum(v['status'] == 'completed' for v in values),
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_command_center(self):
        return self.env['membership.command.center'].action_open_command_center()

    def action_open_risk_center(self):
        return self.env['membership.risk.center'].action_open_center()


class MembershipDecisionCenterLine(models.TransientModel):
    _name = 'membership.decision.center.line'
    _description = 'سطر قرار تنفيذي'
    _order = 'sequence, current_value desc'

    center_id = fields.Many2one('membership.decision.center', required=True, ondelete='cascade')
    scope_type = fields.Selection(
        [('central', 'مركزي'), ('company', 'نقابة فرعية')], string='نطاق القرار', required=True)
    scope_label = fields.Char(string='وصف النطاق', required=True)
    company_id = fields.Many2one('res.company', string='النقابة الفرعية')
    decision_category = fields.Selection([
        ('data', 'البيانات'), ('financial', 'مالي'), ('administrative', 'إداري'),
        ('operational', 'تشغيلي'), ('membership', 'العضوية'), ('fund', 'الصناديق'),
        ('compliance', 'الالتزام')], string='الفئة')
    title = fields.Char(string='العنوان', required=True)
    problem_description = fields.Text(string='المشكلة')
    current_value = fields.Float(string='القيمة الحالية')
    percentage_value = fields.Float(string='النسبة')
    has_percentage = fields.Boolean(string='تتوفر نسبة')
    impact_description = fields.Text(string='التأثير')
    recommendation = fields.Text(string='التوصية الإدارية')
    suggested_action = fields.Text(string='الإجراء التنفيذي المقترح')
    priority = fields.Selection(PRIORITIES, string='الأولوية')
    severity = fields.Selection(PRIORITIES, string='الخطورة')
    responsible_role = fields.Char(string='الدور المسؤول المقترح')
    responsible_user_id = fields.Many2one('res.users', string='المسؤول')
    responsible_display_name = fields.Char(
        string='المسؤول المعروض', compute='_compute_responsible_display_name')
    expected_duration = fields.Char(string='المدة المتوقعة')
    due_date = fields.Date(string='تاريخ الاستحقاق')
    due_date_display = fields.Char(string='تاريخ الاستحقاق', compute='_compute_due_date_display')
    related_model = fields.Char()
    related_domain = fields.Text()
    sequence = fields.Integer()
    status = fields.Selection([
        ('proposed', 'مقترح'), ('under_review', 'قيد المراجعة'), ('accepted', 'معتمد'),
        ('dismissed', 'مرفوض'), ('completed', 'مكتمل')], string='الحالة', default='proposed')
    rule_code = fields.Char()
    rule_reason = fields.Text()
    confidence_level = fields.Selection(CONFIDENCE, string='مستوى الثقة')
    activity_id = fields.Many2one('mail.activity', readonly=True)
    related_risk_id = fields.Many2one('membership.executive.risk', string='الخطر المرتبط')

    @api.depends('responsible_user_id')
    def _compute_responsible_display_name(self):
        for line in self:
            line.responsible_display_name = (
                line.responsible_user_id.partner_id.display_name
                if line.responsible_user_id else _('غير معين'))

    @api.depends('due_date')
    def _compute_due_date_display(self):
        for line in self:
            line.due_date_display = line.due_date.strftime('%d-%m-%Y') if line.due_date else _('غير محدد')

    def _logical_key(self):
        self.ensure_one()
        company_id = self.company_id.id or self.center_id.company_id.id or False
        period = '%s:%s' % (self.center_id.date_from or '', self.center_id.date_to or '')
        return '%s:%s:%s:%s' % (self.rule_code, self.scope_type, company_id or 0, period)

    def _persistent(self, state='accepted'):
        self.ensure_one()
        key = self._logical_key()
        record = self.env['membership.executive.decision'].search([('logical_key', '=', key)], limit=1)
        vals = {
            'name': self.title, 'scope_type': self.scope_type, 'scope_label': self.scope_label,
            'company_id': self.company_id.id or self.center_id.company_id.id or False,
            'source_rule_code': self.rule_code, 'logical_key': key, 'description': self.problem_description,
            'recommendation': self.recommendation, 'priority': self.priority,
            'priority_rank': {'critical': 0, 'high': 10, 'medium': 20, 'low': 30}.get(self.priority, 30),
            'responsible_user_id': self.responsible_user_id.id,
            'state': state, 'source_model': self.related_model, 'source_domain': self.related_domain,
            'related_risk_id': self.related_risk_id.id,
        }
        if not record or record.state not in ('under_review', 'accepted', 'completed'):
            vals['due_date'] = self.due_date
        if record:
            record.write(vals)
        else:
            record = self.env['membership.executive.decision'].create(vals)
        return record

    def action_accept(self):
        for line in self:
            line._persistent('accepted')
            line.status = 'accepted'

    def action_dismiss(self):
        for line in self:
            line._persistent('dismissed')
            line.status = 'dismissed'

    def action_complete(self):
        for line in self:
            record = line._persistent('completed')
            record.completion_date = fields.Datetime.now()
            line.status = 'completed'

    def action_create_activity(self):
        self.ensure_one()
        if not self.responsible_user_id:
            raise UserError(_('حدد المستخدم المسؤول أولًا.'))
        record = self._persistent('accepted')
        activity = record.activity_schedule(
            'mail.mail_activity_data_todo', user_id=self.responsible_user_id.id,
            date_deadline=self.due_date or fields.Date.context_today(self),
            summary=self.title, note=self.recommendation)
        self.activity_id = activity

    def action_open_source(self):
        self.ensure_one()
        domain = json.loads(self.related_domain or '[]')
        return self.env['membership.executive.metrics.service']._open_domain(
            self.related_model, self.title, domain)

    def action_open_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': self.title,
            'res_model': self._name, 'res_id': self.id, 'view_mode': 'form',
            'target': 'current',
        }
