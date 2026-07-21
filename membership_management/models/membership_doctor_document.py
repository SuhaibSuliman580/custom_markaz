from odoo import api, fields, models, _
from odoo.exceptions import AccessError


class MembershipDoctorDocument(models.Model):
    _name = 'membership.doctor.document'
    _description = 'وثيقة طبيب معتمدة من طلب جمع البيانات'
    _order = 'document_type, id'

    partner_id = fields.Many2one('res.partner', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='partner_id.company_id', store=True, readonly=True)
    source_request_id = fields.Many2one('membership.profile.update', required=True, readonly=True, ondelete='restrict')
    source_document_id = fields.Many2one('membership.profile.document', required=True, readonly=True, ondelete='restrict')
    document_type = fields.Selection(related='source_document_id.document_type', store=True, readonly=True)
    file_data = fields.Binary(related='source_document_id.file_data', readonly=True)
    file_name = fields.Char(related='source_document_id.file_name', readonly=True)
    document_name = fields.Char(related='source_document_id.document_name', store=True, readonly=True)
    document_number = fields.Char(related='source_document_id.document_number', store=True, readonly=True)
    issue_date = fields.Date(related='source_document_id.issue_date', store=True, readonly=True)
    expiry_date = fields.Date(related='source_document_id.expiry_date', store=True, readonly=True)
    issuing_authority = fields.Char(related='source_document_id.issuing_authority', store=True, readonly=True)
    verification_state = fields.Selection(
        related='source_document_id.verification_state', store=True, readonly=True,
    )
    employee_note = fields.Char(related='source_document_id.employee_note', readonly=True)

    _sql_constraints = [
        ('source_document_unique', 'unique(source_document_id)', 'تم نقل هذه الوثيقة إلى ملف الطبيب مسبقًا.'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        if not self.env.context.get('profile_execution'):
            raise AccessError(_('وثائق الطبيب المعتمدة تُنشأ بواسطة تنفيذ الطلب فقط.'))
        return super().create(vals_list)

    def write(self, vals):
        raise AccessError(_('وثيقة الطبيب المعتمدة للقراءة فقط.'))

    def unlink(self):
        raise AccessError(_('لا يمكن حذف وثيقة الطبيب المعتمدة من هذا المسار.'))
