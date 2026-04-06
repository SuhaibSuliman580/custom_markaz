from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    membership_initial_product_id = fields.Many2one(
        'product.product',
        string='Initial Membership Product',
        config_parameter='membership_management.initial_product_id',
        domain=[('type', '=', 'service')],
        help='Product used for the first membership (application fee / initial subscription).',
    )

    membership_renewal_product_ids = fields.Many2many(
        'product.product',
        string='Renewal Products',
        relation='membership_management_settings_renewal_product_rel',
        column1='settings_id',
        column2='product_id',
        help='Products allowed for membership renewal invoices (employee selects one).',
    )

    def get_values(self):
        res = super().get_values()
        icp = self.env['ir.config_parameter'].sudo()
        ids_str = icp.get_param('membership_management.renewal_product_ids', default='')
        renewal_ids = [int(x) for x in ids_str.split(',') if x.strip().isdigit()]
        res.update({
            'membership_renewal_product_ids': [(6, 0, renewal_ids)],
        })
        return res

    def set_values(self):
        super().set_values()
        icp = self.env['ir.config_parameter'].sudo()
        ids_str = ','.join(str(i) for i in self.membership_renewal_product_ids.ids)
        icp.set_param('membership_management.renewal_product_ids', ids_str)
