from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MembershipRenewalWizard(models.TransientModel):
    _name = 'membership.renewal.wizard'
    _description = 'Membership Renewal Wizard'

    period_id = fields.Many2one('membership.period', string='Membership Period', required=True, readonly=True)
    partner_id = fields.Many2one(related='period_id.partner_id', string='Doctor', readonly=True)

    renewal_template_id = fields.Many2one(
        'invoice.service.template',
        string='Renewal Template',
        required=True,
        domain="[('id', 'in', allowed_renewal_template_ids)]",
    )

    allowed_renewal_template_ids = fields.Many2many(
        'invoice.service.template',
        compute='_compute_allowed_templates',
        string='Allowed Renewal Templates',
    )

    @api.depends('period_id')
    def _compute_allowed_templates(self):
        icp = self.env['ir.config_parameter'].sudo()
        ids_list = [int(x) for x in icp.get_param('membership_management.renewal_template_ids', default='').split(',') if x.strip().isdigit()]
        templates = self.env['invoice.service.template'].browse(ids_list).exists() if ids_list else self.env['invoice.service.template'].search([])
        for wiz in self:
            wiz.allowed_renewal_template_ids = templates.filtered(lambda t: not t.company_id or t.company_id == wiz.env.company)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if not res.get('period_id') and self.env.context.get('default_period_id'):
            res['period_id'] = self.env.context['default_period_id']
        try:
            wiz = self.new(res)
            wiz._compute_allowed_templates()
            if not res.get('renewal_template_id') and len(wiz.allowed_renewal_template_ids) == 1:
                res['renewal_template_id'] = wiz.allowed_renewal_template_ids.id
        except Exception:
            pass
        return res

    def action_confirm(self):
        self.ensure_one()
        period = self.period_id
        if period.state != 'active':
            raise UserError(_('You can only renew an active membership period.'))
        if not self.renewal_template_id:
            raise UserError(_('Please select a renewal template.'))
        if not self.renewal_template_id.line_ids:
            raise UserError(_('The selected renewal template has no lines.'))

        invoice = self.env['account.move'].sudo().create({
            'move_type': 'out_invoice',
            'partner_id': period.partner_id.id,
        })
        self.renewal_template_id.action_apply_to_invoice(invoice, replace_existing=True)

        period.sudo().write({
            'invoice_id': invoice.id,
            'period_type': 'renewal',
            'renewal_template_id': self.renewal_template_id.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Renewal Invoice'),
            'res_model': 'account.move',
            'res_id': invoice.id,
            'view_mode': 'form',
            'target': 'current',
        }
