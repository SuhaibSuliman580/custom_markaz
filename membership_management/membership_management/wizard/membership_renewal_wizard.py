from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MembershipRenewalWizard(models.TransientModel):
    _name = 'membership.renewal.wizard'
    _description = 'Membership Renewal Wizard'

    period_id = fields.Many2one('membership.period', string='Membership Period', required=True, readonly=True)
    partner_id = fields.Many2one(related='period_id.partner_id', string='Doctor', readonly=True)

    product_id = fields.Many2one(
        'product.product',
        string='Renewal Product',
        required=True,
        domain="[('id', 'in', allowed_renewal_product_ids), ('type','=','service')]",
    )

    allowed_renewal_product_ids = fields.Many2many(
        'product.product',
        compute='_compute_allowed_products',
        string='Allowed Renewal Products',
    )

    @api.depends('period_id')
    def _compute_allowed_products(self):
        icp = self.env['ir.config_parameter'].sudo()
        ids_str = icp.get_param('membership_management.renewal_product_ids', default='')
        ids_list = [int(x) for x in ids_str.split(',') if x.strip().isdigit()]
        if ids_list:
            products = self.env['product.product'].browse(ids_list).exists()
        else:
            # Fallback: allow any saleable service product if settings not configured yet.
            products = self.env['product.product'].search([
                ('type', '=', 'service'),
                ('sale_ok', '=', True),
            ])
        for wiz in self:
            wiz.allowed_renewal_product_ids = products

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        period_id = res.get('period_id')
        if not period_id and self.env.context.get('default_period_id'):
            res['period_id'] = self.env.context['default_period_id']
        # If only one allowed product, preselect it.
        try:
            wiz = self.new(res)
            wiz._compute_allowed_products()
            if not res.get('product_id') and len(wiz.allowed_renewal_product_ids) == 1:
                res['product_id'] = wiz.allowed_renewal_product_ids.id
        except Exception:
            pass
        return res

    def action_confirm(self):
        self.ensure_one()
        period = self.period_id
        if period.state != 'active':
            raise UserError(_('You can only renew an active membership period.'))
        if not self.product_id:
            raise UserError(_('Please select a renewal product.'))

        invoice_vals = {
            'move_type': 'out_invoice',
            'partner_id': period.partner_id.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_id.id,
                'name': _('Membership Renewal - %s') % (period.name or ''),
                'quantity': 1,
                'price_unit': self.product_id.lst_price,
            })],
        }
        invoice = self.env['account.move'].sudo().create(invoice_vals)

        # Link the invoice to the period (use sudo to allow membership officers to trigger renewal)
        period.sudo().write({
            'invoice_id': invoice.id,
            'period_type': 'renewal',
            'product_id': self.product_id.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
