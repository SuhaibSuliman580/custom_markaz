from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MembershipApplication(models.Model):
    _name = 'membership.application'
    _description = 'Membership Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference', required=True, readonly=True,
        default=lambda self: _('New'), copy=False,
    )
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
    notes = fields.Text(string='Notes')
    officer_notes = fields.Text(string='Officer Notes')
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True, copy=False)
    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state', string='Payment Status',
    )
    membership_period_id = fields.Many2one(
        'membership.period', string='Membership Period', readonly=True, copy=False,
    )
    attachment_ids = fields.Many2many(
        'ir.attachment', string='Attachments',
        help='Upload required documents for the application.',
    )

    # ── Related fields from partner (Doctor Info) ──
    # Personal
    doctor_arabic_name = fields.Char(related='partner_id.arabic_name', string='Name (Arabic)', readonly=True)
    doctor_national_id = fields.Char(related='partner_id.national_id', string='National ID / Iqama', readonly=True)
    doctor_birth_date = fields.Date(related='partner_id.birth_date', string='Date of Birth', readonly=True)
    doctor_gender = fields.Selection(related='partner_id.gender', string='Gender', readonly=True)
    doctor_nationality_id = fields.Many2one(related='partner_id.nationality_id', string='Nationality', readonly=True)
    doctor_email = fields.Char(related='partner_id.email', string='Email', readonly=True)
    doctor_phone = fields.Char(related='partner_id.phone', string='Phone', readonly=True)
    doctor_mobile = fields.Char(related='partner_id.mobile', string='Mobile', readonly=True)

    # Medical Qualifications
    # doctor_specialty = fields.Selection(related='partner_id.medical_specialty', string='Specialty', readonly=True)
    doctor_specialty_id = fields.Many2one(related='partner_id.medical_specialty_id', string='Specialty', readonly=True)
    doctor_qualification = fields.Selection(related='partner_id.qualification', string='Qualification', readonly=True)
    doctor_university = fields.Char(related='partner_id.university', string='University', readonly=True)
    doctor_graduation_year = fields.Char(related='partner_id.graduation_year', string='Graduation Year', readonly=True)

    # License
    doctor_license_no = fields.Char(related='partner_id.medical_license_no', string='License No.', readonly=True)
    doctor_license_issue = fields.Date(related='partner_id.license_issue_date', string='License Issue Date', readonly=True)
    doctor_license_expiry = fields.Date(related='partner_id.license_expiry_date', string='License Expiry Date', readonly=True)

    # Employment
    doctor_workplace = fields.Char(related='partner_id.workplace_name', string='Workplace', readonly=True)
    doctor_workplace_type = fields.Selection(related='partner_id.workplace_type', string='Workplace Type', readonly=True)
    doctor_experience = fields.Integer(related='partner_id.years_of_experience', string='Experience (Years)', readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'membership.application'
                ) or _('New')
        return super().create(vals_list)

    def action_approve(self):
        """Approve the application and create an invoice."""
        for rec in self:
            if rec.state != 'draft' and rec.state != 'need_info':
                raise UserError(_('Only applications under review or needing info can be approved.'))
            invoice = rec._create_membership_invoice()
            rec.write({
                'state': 'approved',
                'invoice_id': invoice.id,
            })
        return True

    def action_reject(self):
        """Reject the application."""
        for rec in self:
            if rec.state not in ('draft', 'need_info'):
                raise UserError(_('Only applications under review or needing info can be rejected.'))
            rec.write({'state': 'rejected'})
        return True

    def action_request_info(self):
        """Request more information from the applicant."""
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_('Only applications under review can request more info.'))
            rec.write({'state': 'need_info'})
        return True

    def action_reset_to_draft(self):
        """Reset application back to Under Review."""
        for rec in self:
            if rec.state == 'need_info':
                rec.write({'state': 'draft'})
        return True

    def action_view_invoice(self):
        """Open the related invoice."""
        self.ensure_one()
        if not self.invoice_id:
            raise UserError(_('No invoice found for this application.'))
        return {
            'type': 'ir.actions.act_window',
            'name': _('Membership Invoice'),
            'res_model': 'account.move',
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_activate_membership(self):
        """Manual activation: force-check if invoice is paid and activate."""
        for rec in self:
            if rec.membership_period_id:
                raise UserError(_('Membership already activated for this application.'))
            if not rec.invoice_id:
                raise UserError(_('No invoice found. Please approve the application first.'))
            if rec.invoice_id.payment_state not in ('paid', 'in_payment'):
                raise UserError(_('Invoice is not yet paid. Payment state: %s') % rec.invoice_id.payment_state)
            rec.invoice_id._activate_membership_if_applicable()
        return True

    def _create_membership_invoice(self):
        """Create a customer invoice for the membership product."""
        self.ensure_one()
        product = self.env.ref('membership_management.membership_product')
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': product.name,
                'quantity': 1,
                'price_unit': product.list_price,
            })],
        }
        invoice = self.env['account.move'].sudo().create(invoice_vals)
        return invoice
