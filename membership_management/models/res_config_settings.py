from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    membership_initial_template_ids = fields.Many2many(
        'invoice.service.template',
        string='Initial Membership Templates',
        relation='membership_mgmt_settings_initial_template_rel',
        column1='settings_id',
        column2='template_id',
        help='Templates available for initial membership invoices.',
    )

    membership_default_initial_template_id = fields.Many2one(
        'invoice.service.template',
        string='Default Initial Membership Template',
        config_parameter='membership_management.default_initial_template_id',
        help='Default template used for new membership applications when no template is selected manually.',
    )

    membership_renewal_template_ids = fields.Many2many(
        'invoice.service.template',
        string='Renewal Templates',
        relation='membership_mgmt_settings_renewal_template_rel',
        column1='settings_id',
        column2='template_id',
        help='Templates allowed for membership renewal invoices.',
    )

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()
        initial_ids = [int(x) for x in icp.get_param('membership_management.initial_template_ids', default='').split(',') if x.strip().isdigit()]
        renewal_ids = [int(x) for x in icp.get_param('membership_management.renewal_template_ids', default='').split(',') if x.strip().isdigit()]
        res.update({
            'membership_initial_template_ids': [(6, 0, initial_ids)],
            'membership_renewal_template_ids': [(6, 0, renewal_ids)],
        })
        return res

    def set_values(self):
        super().set_values()
        icp = self.env['ir.config_parameter'].sudo()
        icp.set_param('membership_management.initial_template_ids', ','.join(str(i) for i in self.membership_initial_template_ids.ids))
        icp.set_param('membership_management.renewal_template_ids', ','.join(str(i) for i in self.membership_renewal_template_ids.ids))
