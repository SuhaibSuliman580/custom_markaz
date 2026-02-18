from odoo import models, fields


class HrKitchen(models.Model):
    _name = 'hr.kitchen'
    _description = 'HR Kitchen'

    name = fields.Char(string='Title', required=True, translate=True)
    responsible_id = fields.Many2one('res.partner', string='Responsible', index=True,
                                     help="The partner who manages this kitchen and will get notified when a meal order is confirmed.\n"
                                     "The partner can also approve confirmed orders.")
