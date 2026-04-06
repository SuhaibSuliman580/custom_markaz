import base64
import io
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
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

    period_type = fields.Selection([
        ('initial', 'Initial'),
        ('renewal', 'Renewal'),
    ], string='Period Type', default='initial', required=True, tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly=True)
    application_id = fields.Many2one(
        'membership.application', string='Application', readonly=True,
    )
    qr_code = fields.Binary(string='QR Code', readonly=True, attachment=True)
    product_id = fields.Many2one(
        'product.product', string='Membership Product', required=False,
        domain="[('type','=','service')]",
        help="The product used for invoicing this membership period."
    )

    @api.model
    def _get_initial_product(self):
        """Return the configured initial product, falling back to module demo product."""
        icp = self.env['ir.config_parameter'].sudo()
        pid = icp.get_param('membership_management.initial_product_id')
        if pid and str(pid).isdigit():
            product = self.env['product.product'].browse(int(pid)).exists()
            if product:
                return product
        return self.env.ref('membership_management.membership_product', raise_if_not_found=False)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        # If period is created manually and is initial, prefill the initial product.
        if 'period_type' in fields_list and res.get('period_type', 'initial') == 'initial':
            if 'product_id' in fields_list and not res.get('product_id'):
                product = self._get_initial_product()
                if product:
                    res['product_id'] = product.id
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('period_type', 'initial') == 'initial' and not vals.get('product_id'):
                product = self._get_initial_product()
                if product:
                    vals['product_id'] = product.id
        return super().create(vals_list)

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
        """Open the renewal wizard so the employee selects one of the allowed renewal products."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Create Renewal Invoice'),
            'res_model': 'membership.renewal.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_period_id': self.id,
            }
        }
