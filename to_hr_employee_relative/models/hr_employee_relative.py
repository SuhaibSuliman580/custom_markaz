from odoo import models, fields, api


class HrEmployeeRelative(models.Model):
    _name = 'hr.employee.relative'
    _description = 'Employee Relative'
    _rec_name = 'contact_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, ondelete='cascade')
    contact_id = fields.Many2one('res.partner', string='Relative Contact', required=True, ondelete='cascade', index=True)
    type = fields.Selection([
        ('father', 'Father'),
        ('mother', 'Mother'),
        ('wife', 'Wife'),
        ('husband', 'Husband'),
        ('children', 'Children'),
        ('friend', 'Friend'),
        ('other', 'Others')
        ], string='Relation Type', required=True)
    is_dependant = fields.Boolean('Is Dependant', default=False)
    relative_email = fields.Char(related='contact_id.email', readonly=False)
    relative_phone = fields.Char(related='contact_id.phone', readonly=False)
    relative_mobile = fields.Char(related='contact_id.mobile', readonly=False)
    relative_vat = fields.Char(related='contact_id.vat', readonly=False)

    _sql_constraints = [
        ('employee_contact_unique',
         'UNIQUE(employee_id,contact_id)',
         "Employee and Relative Contact must be unique"),
    ]

    @api.constrains('type')
    def _check_marital_partner(self):
        self.employee_id._check_marital_partner()

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = ['|', ('employee_id.name', operator, name), ('contact_id.name', operator, name)]
        recs = self.search(domain + args, limit=limit)
        return [(record.id, record.display_name) for record in recs.sudo()]
