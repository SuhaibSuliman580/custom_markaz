from odoo import models, fields

class MedicalUnv(models.Model):
    _name = 'medical.unv'
    _description = 'Universities'
    _rec_name = 'name'

    name = fields.Char(string='University Name', required=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)
