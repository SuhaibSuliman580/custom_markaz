from odoo import fields, models


class MedicalSpecialty(models.Model):
    _name = 'medical.specialty'
    _description = 'Medical Specialty'
    _order = 'name'

    name = fields.Char(string='Specialty Name', required=True, translate=True)
    code = fields.Char(string='Code')
    active = fields.Boolean(default=True)