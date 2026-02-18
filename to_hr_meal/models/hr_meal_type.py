from odoo import models, fields


class HrMealType(models.Model):
    _name = 'hr.meal.type'
    _description = 'HR Meal Type'
    _inherit = ['mail.thread']

    name = fields.Char(string='Title', required=True, translate=True)
    scheduled_hour = fields.Float(string='Scheduled Hour')
    price = fields.Float(string='Price', default=0.0, required=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('name_unique',
         'UNIQUE(name)',
         "The meal type's title must be unique"),
    ]
