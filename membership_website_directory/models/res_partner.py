from odoo import models, fields

class ResPartner(models.Model):
    _inherit = 'res.partner'
    is_public_member = fields.Boolean(default=False)
