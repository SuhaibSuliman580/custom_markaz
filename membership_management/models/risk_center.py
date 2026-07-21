import json
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from .decision_center import CONFIDENCE


class ExecutiveRisk(models.Model):
    _name = 'membership.executive.risk'
    _description = 'مخاطرة تنفيذية'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'risk_score desc, create_date desc'

    name = fields.Char(required=True, tracking=True)
    scope_type = fields.Selection(
        [('central', 'مركزي'), ('company', 'نقابة فرعية')],
        string='نطاق الخطر', required=True, default='company', index=True)
    scope_label = fields.Char(string='وصف النطاق', required=True, default='مركزي')
    company_id = fields.Many2one('res.company', string='النقابة الفرعية', index=True)
    source_rule_code = fields.Char(required=True, index=True)
    logical_key = fields.Char(required=True, index=True)
    description = fields.Text(string='الوصف', required=True)
    mitigation = fields.Text(string='إجراء المعالجة', required=True)
    risk_level = fields.Selection([
        ('critical', 'حرج'), ('high', 'مرتفع'), ('medium', 'متوسط'), ('low', 'منخفض')], tracking=True)
    risk_state = fields.Selection(
        [('potential', 'محتمل'), ('realized', 'متحقق')], required=True, default='realized')
    risk_score = fields.Integer(string='درجة الخطر')
    score_reason = fields.Text()
    probability_reason = fields.Text()
    impact_reason = fields.Text()
    responsible_user_id = fields.Many2one('res.users', string='المسؤول', tracking=True)
    responsible_role = fields.Char(string='الدور المسؤول المقترح')
    due_date = fields.Date(string='تاريخ الاستحقاق', tracking=True)
    state = fields.Selection([
        ('acknowledged', 'تم الإقرار'), ('mitigation_in_progress', 'قيد المعالجة'),
        ('resolved', 'محلول'), ('accepted', 'مقبول')],
        string='الحالة', default='acknowledged', tracking=True)
    mitigation_status = fields.Selection([
        ('not_started', 'لم تبدأ'), ('in_progress', 'قيد المعالجة'),
        ('done', 'مكتملة'), ('accepted', 'مقبولة')],
        string='حالة المعالجة', default='not_started', required=True, tracking=True)
    source_model = fields.Char()
    source_domain = fields.Text()
    created_from_center = fields.Boolean(default=True)
    completion_date = fields.Datetime(string='تاريخ الإكمال', readonly=True)
    related_decision_id = fields.Many2one(
        'membership.executive.decision', string='القرار المرتبط')
    _sql_constraints = [('logical_key_unique', 'unique(logical_key)', 'يوجد خطر محفوظ لهذا المؤشر والفترة بالفعل.')]

    def action_resolve(self):
        self.write({
            'state': 'resolved', 'mitigation_status': 'done',
            'completion_date': fields.Datetime.now(),
        })

    @api.constrains('scope_type', 'company_id')
    def _check_company_scope(self):
        for record in self:
            if record.scope_type == 'company' and not record.company_id:
                raise UserError(_('يجب تحديد النقابة الفرعية للخطر الفرعي.'))


class MembershipRiskCenter(models.TransientModel):
    _name = 'membership.risk.center'
    _description = 'مركز المخاطر'
    _inherit = 'membership.workspace.mixin'

    name = fields.Char(default='مركز المخاطر', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='النقابة الفرعية',
        domain=lambda s: [('id', 'in', s.env.companies.ids)])
    date_from = fields.Date(string='من تاريخ')
    date_to = fields.Date(string='إلى تاريخ', default=fields.Date.context_today)
    risk_category = fields.Selection([
        ('financial', 'مالية'), ('data', 'بيانات'), ('administrative', 'إدارية'),
        ('operational', 'تشغيلية'), ('membership', 'عضوية'), ('fund', 'صناديق'),
        ('compliance', 'التزام'), ('system', 'نظام')], string='الفئة')
    risk_level_filter = fields.Selection([
        ('critical', 'حرج'), ('high', 'مرتفع'), ('medium', 'متوسط'), ('low', 'منخفض')], string='مستوى الخطر')
    status_filter = fields.Selection([
        ('open', 'مفتوح'), ('acknowledged', 'تم الإقرار'),
        ('mitigation_in_progress', 'قيد المعالجة'), ('resolved', 'محلول'),
        ('accepted', 'مقبول')], string='الحالة')
    risk_state_filter = fields.Selection(
        [('potential', 'محتمل'), ('realized', 'متحقق')], string='حالة الخطر')
    line_ids = fields.One2many('membership.risk.center.line', 'center_id', readonly=True)
    critical_count = fields.Integer(readonly=True)
    high_count = fields.Integer(readonly=True)
    medium_count = fields.Integer(readonly=True)
    low_count = fields.Integer(readonly=True)
    open_count = fields.Integer(readonly=True)
    treatment_count = fields.Integer(readonly=True)
    resolved_count = fields.Integer(readonly=True)

    @classmethod
    def _compute_risk_score(cls, probability, impact):
        return {'low': 1, 'medium': 2, 'high': 3}[probability] * {
            'low': 1, 'medium': 2, 'high': 3, 'critical': 4}[impact]

    @classmethod
    def _get_risk_level(cls, score):
        return 'critical' if score >= 9 else ('high' if score >= 6 else ('medium' if score >= 3 else 'low'))

    def _risk(self, code, category, title, description, value, percentage, probability,
              impact, mitigation, source_model, domain, confidence='medium', company_id=False,
              risk_state='realized', probability_reason=False, impact_reason=False):
        probability_weight = probability or ('high' if risk_state == 'realized' else 'medium')
        score = self._compute_risk_score(probability_weight, impact)
        probability_text = probability_reason or (
            _('المشكلة مرصودة فعليًا؛ لا يُعرض احتمال وقوعها لأنها متحققة.')
            if risk_state == 'realized'
            else _('احتمال الوقوع مقدر من المؤشرات التشغيلية الحالية.'))
        impact_text = impact_reason or _('اختير مستوى التأثير وفق حجم السجلات المتأثرة وأثرها التشغيلي.')
        scope_type = 'company' if company_id else 'central'
        scope_label = (
            self.env['res.company'].browse(company_id).display_name
            if company_id else _('جميع النقابات المسموحة'))
        return {
            'company_id': company_id, 'scope_type': scope_type, 'scope_label': scope_label,
            'risk_category': category, 'title': title,
            'description': description, 'current_value': value, 'percentage_value': percentage,
            'has_percentage': percentage is not False,
            'severity': self._get_risk_level(score),
            'risk_state': risk_state,
            'probability': probability if risk_state == 'potential' else False, 'impact': impact,
            'risk_score': score, 'risk_level': self._get_risk_level(score),
            'score_reason': _('درجة الترتيب = وزن التحقق/الاحتمال × وزن التأثير؛ ولا تمثل حكمًا محاسبيًا نهائيًا.'),
            'probability_reason': probability_text, 'impact_reason': impact_text,
            'source_model': source_model, 'source_domain': json.dumps(domain, ensure_ascii=False),
            'mitigation_action': mitigation, 'due_date': fields.Date.today() + timedelta(days=7),
            'responsible_role': self._responsible_role_for_category(category),
            'status': 'open', 'sequence': 12 - score, 'detected_date': fields.Date.today(),
            'last_evaluated_date': fields.Datetime.now(), 'rule_code': code, 'confidence_level': confidence,
        }

    @api.model
    def _responsible_role_for_category(self, category):
        return {
            'data': _('مدير العضوية'), 'membership': _('مدير العضوية'),
            'compliance': _('مدير العضوية'), 'financial': _('المسؤول المالي'),
            'fund': _('مدير المالية'), 'administrative': _('المدير الإداري'),
            'operational': _('رئيس القسم أو المدير الإداري'),
        }.get(category, _('غير معين'))

    def _generate_risks(self, m):
        risks = []
        data_rules = [
            ('risk_missing_specialty', 'data', _('ارتفاع نقص الاختصاص'), 'doctor_missing_specialty',
             'doctor_missing_specialty_rate', 20, 'medium', 'high', _('استكمال اختصاصات الأطباء.'), 'res.partner'),
            ('risk_missing_national', 'compliance', _('نقص الرقم الوطني'), 'doctor_missing_national_id',
             'doctor_missing_national_rate', 5, 'medium', 'high', _('تدقيق الهوية واستكمال الرقم الوطني.'), 'res.partner'),
            ('risk_duplicate_national', 'data', _('أرقام وطنية مكررة'), 'doctor_duplicate_national_id',
             'doctor_duplicate_rate', 0, 'high', 'critical', _('مراجعة السجلات المكررة.'), 'res.partner'),
            ('risk_incomplete_profiles', 'data', _('انخفاض اكتمال الملفات'), 'doctor_incomplete_count',
             False, 0, 'medium', 'medium', _('تنفيذ حملة استكمال ملفات.'), 'res.partner'),
            ('risk_overdue_invoice', 'financial', _('فواتير تجاوزت تاريخ الاستحقاق'), 'overdue_invoice_amount',
             False, 0, 'high', 'high', _('إعداد خطة تحصيل للفواتير التي تجاوزت تاريخ الاستحقاق.'), 'account.move'),
            ('risk_draft_moves', 'financial', _('قيود مسودة تجاوزت مهلة المراجعة'), 'aged_draft_move_count',
             False, 0, 'medium', 'high', _('مراجعة القيود المسودة التي تجاوز عمرها سبعة أيام.'), 'account.move'),
            ('risk_distribution', 'fund', _('مشكلات توزيع الإيرادات'), 'distribution_issue_count',
             False, 0, 'high', 'critical', _('مراجعة التوزيع المرتبط بالفواتير.'), 'syndicate.revenue.distribution.ledger.line'),
            ('risk_sla', 'administrative', _('معاملات تجاوزت SLA'), 'request_delayed_count',
             False, 0, 'high', 'high', _('معالجة الأقدم وإعادة توزيع العمل.'), 'membership.service.request'),
            ('risk_unassigned', 'administrative', _('معاملات غير مسندة'), 'unassigned_request_count',
             False, 0, 'medium', 'high', _('تعيين مسؤول للمعاملات المفتوحة.'), 'membership.service.request'),
            ('risk_tasks', 'operational', _('مهام متأخرة'), 'overdue_task_count',
             False, 0, 'medium', 'high', _('مراجعة المهام المتأخرة مع المسؤولين.'), 'mail.activity'),
            ('risk_unassigned_doctors', 'data', _('أطباء بلا شركة'), 'doctor_unassigned_count',
             False, 0, 'medium', 'high', _('ربط الملفات بالشركة الصحيحة.'), 'res.partner'),
        ]
        for code, category, title, value_key, rate_key, threshold, probability, impact, mitigation, model in data_rules:
            value = m.get(value_key) or 0
            percentage = m.get(rate_key, False) if rate_key else False
            applies = percentage >= threshold if rate_key and threshold else value > threshold
            if value and applies:
                description = title
                if code == 'risk_overdue_invoice':
                    description = _('%s فاتورة بقيمة %s تجاوزت تاريخ الاستحقاق.') % (
                        m.get('overdue_invoice_count', 0), value)
                elif code == 'risk_draft_moves':
                    description = _('%s قيدًا مسودة تجاوز مهلة التقادم المحددة (%s أيام).') % (
                        value, m.get('draft_move_age_days', 7))
                domains = {
                    'risk_missing_specialty': [('is_doctor', '=', True), ('medical_specialty_id', '=', False)],
                    'risk_missing_national': [('is_doctor', '=', True), ('national_id', 'in', (False, ''))],
                    'risk_unassigned_doctors': [('is_doctor', '=', True), ('company_id', '=', False)],
                    'risk_overdue_invoice': [
                        ('move_type', '=', 'out_invoice'), ('state', '=', 'posted'),
                        ('payment_state', 'not in', ('paid', 'reversed')),
                        ('invoice_date_due', '<', fields.Date.to_string(fields.Date.context_today(self)))],
                    'risk_draft_moves': [
                        ('state', '=', 'draft'),
                        ('date', '<', fields.Date.to_string(
                            fields.Date.context_today(self) - timedelta(days=m.get('draft_move_age_days', 7))))],
                    'risk_sla': [('state', 'not in', ('completed', 'cancelled'))],
                    'risk_unassigned': [('state', 'not in', ('completed', 'cancelled')),
                                        ('started_by_id', '=', False), ('submitted_by_id', '=', False)],
                }
                risks.append(self._risk(code, category, title, description, value, percentage, probability,
                                        impact, mitigation, model, domains.get(code, []),
                                        m.get('evaluation_confidence') or 'medium',
                                        self.company_id.id or False))
        delayed = m.get('request_delayed_count') or 0
        if delayed:
            for risk in risks:
                if risk['rule_code'] == 'risk_sla':
                    risk['percentage_value'] = m.get('delayed_request_rate') or False
        for branch in m.get('branch_lines', []):
            if branch.get('has_health_score') and branch.get('branch_health_score', 100) < 60:
                company = branch.get('company_id')
                risks.append(self._risk(
                    'risk_low_branch', 'administrative', _('فرع منخفض الأداء'),
                    _('درجة صحة الفرع أقل من الحد المقبول.'), branch['branch_health_score'], 0,
                    'high', 'high', _('طلب خطة تصحيح أسبوعية.'), 'res.company',
                    [['id', '=', company[0]]], branch.get('evaluation_confidence') or 'medium', company[0]))
        for employee in m.get('employee_lines', []):
            load = employee.get('assigned_count', 0)
            if load >= 20:
                user = employee.get('user_id')
                risks.append(self._risk(
                    'risk_employee_workload_%s' % user[0], 'operational', _('ضغط عمل مرتفع'),
                    _('موظف يحمل عددًا مرتفعًا من المعاملات المفتوحة.'), load, 0,
                    'high', 'medium', _('إعادة توزيع جزء من المعاملات أو إضافة دعم مؤقت.'),
                    'res.users', [['id', '=', user[0]]], 'high', self.company_id.id or False))
        return risks

    @api.model
    def action_open_center(self):
        center = self.create({'date_to': fields.Date.context_today(self)})
        center.action_refresh()
        return {'type': 'ir.actions.act_window', 'name': _('مركز المخاطر'),
                'res_model': self._name, 'res_id': center.id, 'view_mode': 'form', 'target': 'current'}

    def action_refresh(self):
        self.ensure_one()
        current = {
            (line.rule_code, line.scope_type, line.company_id.id or 0): {
                'status': line.status, 'due_date': line.due_date,
                'owner_user_id': line.owner_user_id.id,
            }
            for line in self.line_ids
        }
        m = self.env['membership.executive.metrics.service']._get_executive_metrics(
            self.company_id.id, self.date_from, self.date_to)
        values = self._generate_risks(m)
        period = '%s:%s' % (self.date_from or '', self.date_to or '')
        logical_keys = {
            '%s:%s:%s:%s' % (
                value['rule_code'], value['scope_type'],
                value.get('company_id') or 0, period): value
            for value in values
        }
        persisted = self.env['membership.executive.risk'].search(
            [('logical_key', 'in', list(logical_keys))]) if logical_keys else self.env['membership.executive.risk']
        persisted_by_key = {record.logical_key: record for record in persisted}
        for key, value in logical_keys.items():
            local = current.get((
                value['rule_code'], value['scope_type'], value.get('company_id') or 0))
            if local:
                value.update({field: local[field] for field in (
                    'status', 'due_date', 'owner_user_id') if local.get(field)})
            saved = persisted_by_key.get(key)
            if saved:
                value.update({
                    'status': saved.state, 'due_date': saved.due_date,
                    'owner_user_id': saved.responsible_user_id.id,
                    'related_decision_id': saved.related_decision_id.id,
                })
        if self.risk_category:
            values = [v for v in values if v['risk_category'] == self.risk_category]
        if self.risk_level_filter:
            values = [v for v in values if v['risk_level'] == self.risk_level_filter]
        if self.status_filter:
            values = [v for v in values if v['status'] == self.status_filter]
        if self.risk_state_filter:
            values = [v for v in values if v['risk_state'] == self.risk_state_filter]
        self.line_ids = [(5, 0, 0)] + [(0, 0, v) for v in values]
        self.write({
            'critical_count': sum(v['risk_level'] == 'critical' for v in values),
            'high_count': sum(v['risk_level'] == 'high' for v in values),
            'medium_count': sum(v['risk_level'] == 'medium' for v in values),
            'low_count': sum(v['risk_level'] == 'low' for v in values),
            'open_count': len(values), 'treatment_count': 0, 'resolved_count': 0,
        })
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def action_open_decision_center(self):
        return self.env['membership.decision.center'].action_open_center()


class MembershipRiskCenterLine(models.TransientModel):
    _name = 'membership.risk.center.line'
    _description = 'سطر مخاطرة تنفيذية'
    _order = 'sequence, risk_score desc'

    center_id = fields.Many2one('membership.risk.center', required=True, ondelete='cascade')
    scope_type = fields.Selection(
        [('central', 'مركزي'), ('company', 'نقابة فرعية')],
        string='نطاق الخطر', required=True)
    scope_label = fields.Char(string='وصف النطاق', required=True)
    company_id = fields.Many2one('res.company', string='النقابة الفرعية')
    risk_category = fields.Selection([
        ('financial', 'مالية'), ('data', 'بيانات'), ('administrative', 'إدارية'),
        ('operational', 'تشغيلية'), ('membership', 'عضوية'), ('fund', 'صناديق'),
        ('compliance', 'التزام'), ('system', 'نظام')], string='فئة الخطر')
    title = fields.Char(string='العنوان')
    description = fields.Text(string='الوصف')
    current_value = fields.Float(string='القيمة الحالية')
    percentage_value = fields.Float(string='النسبة')
    has_percentage = fields.Boolean(string='تتوفر نسبة')
    severity = fields.Selection([('critical', 'حرج'), ('high', 'مرتفع'), ('medium', 'متوسط'), ('low', 'منخفض')])
    risk_state = fields.Selection([('potential', 'محتمل'), ('realized', 'متحقق')], string='حالة الخطر')
    probability = fields.Selection(
        [('low', 'منخفض'), ('medium', 'متوسط'), ('high', 'مرتفع')], string='الاحتمال')
    impact = fields.Selection(
        [('low', 'منخفض'), ('medium', 'متوسط'), ('high', 'مرتفع'), ('critical', 'حرج')],
        string='التأثير')
    risk_score = fields.Integer(string='درجة الخطر')
    risk_level = fields.Selection(
        [('critical', 'حرج'), ('high', 'مرتفع'), ('medium', 'متوسط'), ('low', 'منخفض')],
        string='مستوى الخطر')
    score_reason = fields.Text(string='سبب درجة الخطر')
    probability_reason = fields.Text(string='سبب الاحتمال')
    impact_reason = fields.Text(string='سبب التأثير')
    source_model = fields.Char()
    source_domain = fields.Text()
    owner_user_id = fields.Many2one('res.users', string='المسؤول')
    responsible_role = fields.Char(string='الدور المسؤول المقترح')
    responsible_display_name = fields.Char(
        string='المسؤول المعروض', compute='_compute_responsible_display_name')
    mitigation_action = fields.Text(string='إجراء المعالجة')
    due_date = fields.Date(string='تاريخ الاستحقاق')
    due_date_display = fields.Char(string='تاريخ الاستحقاق', compute='_compute_due_date_display')
    status = fields.Selection([
        ('open', 'مفتوح'), ('acknowledged', 'تم الإقرار'), ('mitigation_in_progress', 'قيد المعالجة'),
        ('resolved', 'محلول'), ('accepted', 'مقبول')], string='الحالة', default='open')
    sequence = fields.Integer()
    detected_date = fields.Date()
    last_evaluated_date = fields.Datetime()
    rule_code = fields.Char()
    confidence_level = fields.Selection(CONFIDENCE)
    activity_id = fields.Many2one('mail.activity', readonly=True)
    related_decision_id = fields.Many2one(
        'membership.executive.decision', string='القرار المرتبط')

    @api.depends('owner_user_id')
    def _compute_responsible_display_name(self):
        for line in self:
            line.responsible_display_name = (
                line.owner_user_id.partner_id.display_name if line.owner_user_id else _('غير معين'))

    @api.depends('due_date')
    def _compute_due_date_display(self):
        for line in self:
            line.due_date_display = line.due_date.strftime('%d-%m-%Y') if line.due_date else _('غير محدد')

    def _persistent(self, state):
        self.ensure_one()
        company_id = self.company_id.id or self.center_id.company_id.id or False
        period = '%s:%s' % (self.center_id.date_from or '', self.center_id.date_to or '')
        key = '%s:%s:%s:%s' % (
            self.rule_code, self.scope_type, company_id or 0, period)
        record = self.env['membership.executive.risk'].search([('logical_key', '=', key)], limit=1)
        vals = {
            'name': self.title, 'scope_type': self.scope_type, 'scope_label': self.scope_label,
            'company_id': company_id, 'source_rule_code': self.rule_code,
            'logical_key': key, 'description': self.description, 'mitigation': self.mitigation_action,
            'risk_level': self.risk_level, 'risk_score': self.risk_score,
            'risk_state': self.risk_state, 'score_reason': self.score_reason,
            'probability_reason': self.probability_reason, 'impact_reason': self.impact_reason,
            'responsible_user_id': self.owner_user_id.id, 'due_date': self.due_date,
            'responsible_role': self.responsible_role,
            'state': state,
            'mitigation_status': (
                'in_progress' if state == 'mitigation_in_progress'
                else ('done' if state == 'resolved' else 'not_started')),
            'source_model': self.source_model, 'source_domain': self.source_domain,
            'related_decision_id': self.related_decision_id.id,
        }
        if record and (
            record.state == 'resolved'
            or (record.state == 'mitigation_in_progress' and state != 'resolved')
        ):
            return record
        if record:
            record.write(vals)
        else:
            record = self.env['membership.executive.risk'].create(vals)
        return record

    def action_acknowledge(self):
        for line in self:
            line._persistent('acknowledged')
            line.status = 'acknowledged'

    def action_start_mitigation(self):
        for line in self:
            line._persistent('mitigation_in_progress')
            line.status = 'mitigation_in_progress'

    def action_resolve(self):
        for line in self:
            record = line._persistent('resolved')
            record.completion_date = fields.Datetime.now()
            line.status = 'resolved'

    def action_create_activity(self):
        self.ensure_one()
        if not self.owner_user_id:
            raise UserError(_('حدد المستخدم المسؤول أولًا.'))
        record = self._persistent('mitigation_in_progress')
        self.activity_id = record.activity_schedule(
            'mail.mail_activity_data_todo', user_id=self.owner_user_id.id,
            date_deadline=self.due_date or fields.Date.context_today(self),
            summary=self.title, note=self.mitigation_action)

    def action_open_source(self):
        self.ensure_one()
        return self.env['membership.executive.metrics.service']._open_domain(
            self.source_model, self.title, json.loads(self.source_domain or '[]'))

    def action_create_decision(self):
        self.ensure_one()
        risk = self._persistent('acknowledged')
        period = '%s:%s' % (self.center_id.date_from or '', self.center_id.date_to or '')
        key = 'from_%s:%s:%s:%s' % (
            self.rule_code, self.scope_type, self.company_id.id or 0, period)
        decision = self.env['membership.executive.decision'].search(
            [('logical_key', '=', key)], limit=1)
        if not decision:
            decision = self.env['membership.executive.decision'].create({
                'name': self.title,
                'scope_type': self.scope_type, 'scope_label': self.scope_label,
                'company_id': self.company_id.id or False,
                'source_rule_code': 'from_%s' % self.rule_code, 'logical_key': key,
                'description': self.description,
                'recommendation': _('اعتماد خطة معالجة الخطر ومتابعة تنفيذها.'),
                'priority': self.risk_level,
                'priority_rank': {'critical': 0, 'high': 10, 'medium': 20, 'low': 30}[self.risk_level],
                'responsible_user_id': self.owner_user_id.id,
                'due_date': self.due_date, 'state': 'proposed',
                'source_model': self.source_model, 'source_domain': self.source_domain,
                'related_risk_id': risk.id,
            })
        risk.related_decision_id = decision
        self.related_decision_id = decision
        return {
            'type': 'ir.actions.act_window', 'name': _('القرار المرتبط'),
            'res_model': decision._name, 'res_id': decision.id,
            'view_mode': 'form', 'target': 'current',
        }

    def action_open_details(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window', 'name': self.title,
            'res_model': self._name, 'res_id': self.id, 'view_mode': 'form',
            'target': 'current',
        }
