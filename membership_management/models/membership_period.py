import base64
import io

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _


class MembershipPeriod(models.Model):
    _name = 'membership.period'
    _description = 'Membership Period'
    _inherit = ['mail.thread']
    _order = 'start_date desc'

    name = fields.Char(string='Membership Number', readonly=True, copy=False)
    partner_id = fields.Many2one(
        'res.partner', string='Doctor', required=True, tracking=True,
    )
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date', required=True, tracking=True)
    state = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
    ], string='Status', default='active', required=True, tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    application_id = fields.Many2one(
        'membership.application', string='Application', readonly=True,
    )
    qr_code = fields.Binary(string='QR Code', readonly=True, attachment=True)

    def _generate_qr_code(self):
        """Generate QR code containing membership number and partner ID."""
        self.ensure_one()
        try:
            import qrcode
        except ImportError:
            return False

        qr_data = f"MEM:{self.name}|PID:{self.partner_id.id}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        self.qr_code = base64.b64encode(buffer.getvalue())
        return True

    @api.model
    def cron_check_membership_expiration(self):
        """Scheduled action: expire memberships and send reminders."""
        today = fields.Date.today()
        reminder_date = today + relativedelta(days=30)

        # Mark expired memberships
        expired = self.search([
            ('end_date', '<', today),
            ('state', '=', 'active'),
        ])
        for period in expired:
            period.write({'state': 'expired'})
            period.partner_id.write({
                'doctor_membership_state': 'expired',
            })

        # Send reminder for memberships expiring within 30 days
        expiring_soon = self.search([
            ('end_date', '>=', today),
            ('end_date', '<=', reminder_date),
            ('state', '=', 'active'),
        ])
        if expiring_soon:
            template = self.env.ref(
                'membership_management.email_template_membership_expiry_reminder',
                raise_if_not_found=False,
            )
            if template:
                for period in expiring_soon:
                    template.send_mail(period.id, force_send=False)

        return True

    def action_create_renewal_invoice(self):
        """Create a renewal invoice for this membership period."""
        self.ensure_one()
        product = self.env.ref('membership_management.membership_product')
        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': product.id,
                'name': _('Membership Renewal - %s') % self.name,
                'quantity': 1,
                'price_unit': product.list_price,
            })],
        }
        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # Link the invoice — will be processed on payment via account_move override
        self.write({'invoice_id': invoice.id})

        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
