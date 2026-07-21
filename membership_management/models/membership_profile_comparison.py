from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class MembershipProfileComparison(models.Model):
    _name = 'membership.profile.comparison'
    _description = 'مقارنة بيانات طلب الطبيب'
    _order = 'sequence, id'

    request_id = fields.Many2one('membership.profile.update', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='request_id.company_id', store=True, readonly=True)
    sequence = fields.Integer(default=10, readonly=True)
    field_name = fields.Char(required=True, readonly=True)
    field_label = fields.Char(string='الحقل', required=True, readonly=True)
    current_value = fields.Char(string='القيمة الحالية', readonly=True)
    proposed_value = fields.Char(string='القيمة المقترحة', readonly=True)
    difference_state = fields.Selection([
        ('not_entered', 'غير مدخل'), ('new', 'جديد'),
        ('modified', 'معدل'), ('unchanged', 'بدون تغيير'),
        ('review', 'يحتاج مراجعة'),
    ], string='حالة الفرق', required=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('profile_comparison_refresh'):
            raise AccessError(_('سطور المقارنة تُنشأ آليًا من الطلب فقط.'))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.context.get('profile_comparison_refresh'):
            raise AccessError(_('سطور المقارنة للقراءة فقط.'))
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('profile_comparison_refresh'):
            raise AccessError(_('سطور المقارنة تُحدّث آليًا من الطلب فقط.'))
        return super().unlink()
