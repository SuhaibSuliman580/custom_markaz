from odoo import models, fields, api


class HRDepartment(models.Model):
    _name = 'hr.department.register.partner'
    _description = 'Department and Contribution Register Partner Map'

    contribution_register_id = fields.Many2one('hr.contribution.register', string='Contribution Register',
                                               required=True, ondelete='cascade')
    department_id = fields.Many2one('hr.department', string='Department', required=True, ondelete='cascade')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True, ondelete='cascade', index=True)

    _sql_constraints = [
        ('name_template_id',
         'UNIQUE(contribution_register_id,department_id)',
         "Another record of the same Department and Contribution Register exists already!"
         " Please change either the Department or Contribution Register."),
    ]

    @api.depends('department_id', 'contribution_register_id', 'partner_id')
    def _compute_display_name(self):
        for r in self:
            r.display_name = f"{r.department_id.name} - {r.contribution_register_id.name} - {r.partner_id.name}"
