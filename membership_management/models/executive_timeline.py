from datetime import timedelta

from odoo import api, fields, models, _


class MembershipExecutiveTimeline(models.TransientModel):
    _name = 'membership.executive.timeline'
    _description = 'الخط الزمني التنفيذي'

    name = fields.Char(default='الخط الزمني التنفيذي', readonly=True)
    company_id = fields.Many2one(
        'res.company', string='النقابة الفرعية',
        domain=lambda s: [('id', 'in', s.env.companies.ids)])
    period = fields.Selection(
        [('today', 'اليوم'), ('week', 'هذا الأسبوع'), ('month', 'هذا الشهر')],
        string='الفترة', default='today')
    event_type = fields.Selection([
        ('request', 'معاملة'), ('invoice', 'فاتورة'), ('payment', 'قبض'),
        ('distribution', 'توزيع إيراد'), ('decision', 'قرار'), ('risk', 'مخاطرة')],
        string='نوع الحدث')
    user_id = fields.Many2one('res.users', string='الموظف')
    importance = fields.Selection(
        [('critical', 'حرج'), ('high', 'مرتفع'), ('normal', 'عادي')], string='الأهمية')
    line_ids = fields.One2many('membership.executive.timeline.line', 'timeline_id', readonly=True)

    @api.model
    def action_open_timeline(self):
        timeline = self.create({})
        timeline.action_refresh()
        return {'type': 'ir.actions.act_window', 'name': _('الخط الزمني التنفيذي'),
                'res_model': self._name, 'res_id': timeline.id, 'view_mode': 'form', 'target': 'current'}

    @api.model
    def _employee_display_name(self, user):
        if not user:
            return _('غير معين')
        display_name = user.partner_id.display_name or user.display_name
        if user.login == 'admin' or (display_name or '').strip().lower() == 'administrator':
            return _('مدير النظام')
        return display_name

    def action_refresh(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        start = today if self.period == 'today' else (
            today - timedelta(days=today.weekday()) if self.period == 'week' else today.replace(day=1))
        m = self.env['membership.executive.metrics.service']._get_executive_metrics(
            self.company_id.id, start, today)
        values = []
        for event in m['event_lines']:
            event_type = event.get('event_type') or 'request'
            user_id = event['user_id'][0] if event.get('user_id') else False
            user = self.env['res.users'].browse(user_id) if user_id else self.env['res.users']
            event_dt = fields.Datetime.to_datetime(event['event_date'])
            local_dt = fields.Datetime.context_timestamp(self, event_dt) if event_dt else False
            vals = {
                'event_date': event['event_date'], 'event_type': event_type,
                'date_display': local_dt.strftime('%d-%m-%Y') if local_dt else '',
                'time_display': local_dt.strftime('%H:%M') if local_dt else '',
                'description': event['description'], 'company_id': event['company_id'][0] if event.get('company_id') else False,
                'user_id': user_id,
                'employee_display_name': self._employee_display_name(user),
                'related_model': event.get('res_model'), 'related_res_id': event.get('res_id'),
                'importance': 'normal',
            }
            if self.event_type and vals['event_type'] != self.event_type:
                continue
            if self.user_id and vals['user_id'] != self.user_id.id:
                continue
            if self.importance and vals['importance'] != self.importance:
                continue
            values.append(vals)
        values.sort(
            key=lambda vals: fields.Datetime.to_datetime(vals['event_date']) or fields.Datetime.to_datetime('1970-01-01'),
            reverse=True,
        )
        self.line_ids = [(5, 0, 0)] + [(0, 0, vals) for vals in values]
        return {'type': 'ir.actions.client', 'tag': 'reload'}


class MembershipExecutiveTimelineLine(models.TransientModel):
    _name = 'membership.executive.timeline.line'
    _description = 'حدث في الخط الزمني التنفيذي'
    _order = 'event_date desc'

    timeline_id = fields.Many2one('membership.executive.timeline', required=True, ondelete='cascade')
    event_date = fields.Datetime(string='التاريخ والوقت')
    date_display = fields.Char(string='التاريخ')
    time_display = fields.Char(string='الوقت')
    event_type = fields.Selection([
        ('request', 'معاملة'), ('invoice', 'فاتورة'), ('payment', 'قبض'),
        ('distribution', 'توزيع إيراد'), ('decision', 'قرار'), ('risk', 'مخاطرة')],
        string='نوع الحدث')
    description = fields.Char(string='الوصف')
    company_id = fields.Many2one('res.company', string='النقابة الفرعية')
    user_id = fields.Many2one('res.users', string='الموظف')
    employee_display_name = fields.Char(string='اسم الموظف')
    related_model = fields.Char()
    related_res_id = fields.Integer()
    importance = fields.Selection(
        [('critical', 'حرج'), ('high', 'مرتفع'), ('normal', 'عادي')], string='الأهمية')

    def action_open_source(self):
        self.ensure_one()
        return {'type': 'ir.actions.act_window', 'name': self.description, 'res_model': self.related_model,
                'res_id': self.related_res_id, 'view_mode': 'form', 'target': 'current'}
