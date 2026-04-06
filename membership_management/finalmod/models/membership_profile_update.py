
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MembershipProfileUpdate(models.Model):
    _name = 'membership.profile.update'
    _description = 'Membership Profile Update Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(string='Reference', required=True, readonly=True, default=lambda self: _('New'), copy=False)

    partner_id = fields.Many2one(
        'res.partner', string='Doctor', required=True,
        domain=[('is_doctor', '=', True)],
        tracking=True,
    )

    state = fields.Selection([
        ('draft', 'Under Review'),
        ('need_info', 'Need More Information'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    # previous membership state to restore after approval/rejection
    previous_membership_state = fields.Selection([
        ('none', 'No Membership'),
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ], string='Previous Membership Status', readonly=True, copy=False)

    officer_notes = fields.Text(string='Officer Notes')

    # Editable fields (only)
    full_name = fields.Char(string='Full Name', required=True, tracking=True)
    national_id = fields.Char(string='National ID', required=True, tracking=True)
    phone = fields.Char(string='Mobile / Phone', required=True, tracking=True)
    email = fields.Char(string='Email', required=True, tracking=True)
    medical_license_no = fields.Char(string='Registration No. (License)', required=True, tracking=True)
    medical_specialty_id = fields.Many2one('medical.specialty', string='Specialty', required=True, tracking=True)


    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = seq.next_by_code('membership.profile.update') or _('New')
        return super().create(vals_list)

    def action_need_info(self):
        for rec in self:
            rec.state = 'need_info'

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'
            # restore partner state if it was set to pending
            if rec.partner_id and rec.partner_id.doctor_membership_state == 'pending':
                rec.partner_id.doctor_membership_state = rec.previous_membership_state or 'none'

    def action_approve(self):
        for rec in self:
            if rec.state == 'approved':
                continue
            partner = rec.partner_id
            if not partner:
                raise UserError(_("No doctor linked to this request."))
            partner_vals = {
                'name': rec.full_name,
                'national_id': rec.national_id,
                'phone': rec.phone,
                'email': rec.email,
                'medical_license_no': rec.medical_license_no,
                'medical_specialty_id': rec.medical_specialty_id.id,
            }
            partner.write(partner_vals)
            rec.state = 'approved'
            # restore membership status (usually active)
            if partner.doctor_membership_state == 'pending':
                partner.doctor_membership_state = rec.previous_membership_state or 'none'
