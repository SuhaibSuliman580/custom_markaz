import base64

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, ValidationError


class MembershipProfileDocument(models.Model):
    _name = 'membership.profile.document'
    _description = 'وثيقة طلب جمع بيانات طبيب'
    _order = 'document_type, id'

    request_id = fields.Many2one('membership.profile.update', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='request_id.company_id', store=True, readonly=True)
    document_type = fields.Selection([
        ('national_id', 'صورة الهوية'),
        ('medical_license', 'صورة الترخيص الطبي'),
        ('university_certificate', 'صورة الشهادة الجامعية'),
        ('specialty_certificate', 'صورة شهادة الاختصاص'),
        ('previous_membership', 'صورة بطاقة العضوية السابقة'),
        ('personal_photo', 'صورة شخصية'),
        ('other', 'وثيقة إضافية'),
    ], string='نوع الوثيقة', required=True)
    status = fields.Selection([
        ('provided', 'مرفقة'), ('needs_review', 'تحتاج مراجعة'),
        ('missing', 'غير متوفرة'),
    ], string='الحالة', default='provided', required=True)
    file_data = fields.Binary(string='الملف', attachment=True)
    file_name = fields.Char(string='اسم الملف')
    document_name = fields.Char(string='اسم الوثيقة')
    document_number = fields.Char(string='رقم الوثيقة')
    issue_date = fields.Date(string='تاريخ الإصدار')
    expiry_date = fields.Date(string='تاريخ الانتهاء')
    issuing_authority = fields.Char(string='جهة الإصدار')
    verification_state = fields.Selection([
        ('accepted', 'معتمدة'), ('unverified', 'غير متحقق منها'),
        ('rejected', 'مرفوضة'),
    ], string='حالة التحقق', default='accepted', required=True)
    employee_note = fields.Char(string='ملاحظة الموظف')

    @api.constrains('file_data')
    def _check_file_size(self):
        for rec in self.filtered('file_data'):
            try:
                size = len(base64.b64decode(rec.file_data))
            except Exception as exc:
                raise ValidationError(_('ملف الوثيقة غير صالح.')) from exc
            if size > 10 * 1024 * 1024:
                raise ValidationError(_('الحد الأقصى لحجم الوثيقة هو 10 ميغابايت.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request = self.env['membership.profile.update'].browse(vals.get('request_id')).exists()
            if not request or request.state not in request._EDITABLE_STATES or not request._is_employee():
                raise AccessError(_('يمكن لموظف جمع البيانات إضافة الوثائق إلى طلب قابل للتحرير فقط.'))
        return super().create(vals_list)

    def write(self, vals):
        for rec in self:
            if rec.request_id.state not in rec.request_id._EDITABLE_STATES or not rec.request_id._is_employee():
                raise AccessError(_('يمكن تعديل وثائق الطلب القابل للتحرير فقط.'))
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.request_id.state not in rec.request_id._EDITABLE_STATES or not rec.request_id._is_employee():
                raise AccessError(_('يمكن حذف وثائق الطلب القابل للتحرير فقط.'))
        return super().unlink()
