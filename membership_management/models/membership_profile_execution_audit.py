from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class MembershipProfileExecutionAudit(models.Model):
    _name = 'membership.profile.execution.audit'
    _description = 'أثر تنفيذ طلب بيانات طبيب'
    _order = 'id'

    request_id = fields.Many2one('membership.profile.update', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one('res.partner', required=True, readonly=True, index=True)
    company_id = fields.Many2one(related='request_id.company_id', store=True, readonly=True)
    execution_type = fields.Selection([('create', 'إنشاء'), ('update', 'تحديث')], required=True, readonly=True)
    executed_by_id = fields.Many2one('res.users', required=True, readonly=True)
    executed_at = fields.Datetime(required=True, readonly=True)
    field_name = fields.Char(required=True, readonly=True)
    field_label = fields.Char(string='الحقل', required=True, readonly=True)
    old_value = fields.Char(string='القيمة السابقة', readonly=True)
    new_value = fields.Char(string='القيمة الجديدة', readonly=True)
    difference_state = fields.Selection([
        ('new', 'جديد'), ('modified', 'معدل'), ('unchanged', 'بدون تغيير'),
    ], required=True, readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('profile_execution'):
            raise AccessError(_('سجل التنفيذ يُنشأ بواسطة عملية التنفيذ فقط.'))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_('سجل التنفيذ غير قابل للتعديل.'))

    def unlink(self):
        raise AccessError(_('سجل التنفيذ غير قابل للحذف.'))
