from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    employee_relative_ids = fields.One2many('hr.employee.relative', 'contact_id', string='Employee Relatives')
    relative_employee_ids = fields.Many2many('hr.employee', 'partner_relative_employee_rel', 'partner_id', 'employee_id',
                                             string='Relative Employees', compute='_compute_relative_employee_ids', store=True,
                                             help="The employees who are the relatives (e.g. son, wife, etc) of this partner")
    is_employee_relative = fields.Boolean(string='Is Employee Relative', compute='_compute_is_employee_relative', store=True)

    @api.depends('employee_relative_ids.employee_id')
    def _compute_relative_employee_ids(self):
        for r in self:
            r.relative_employee_ids = r.employee_relative_ids.employee_id

    @api.depends('employee_relative_ids')
    def _compute_is_employee_relative(self):
        for r in self:
            r.is_employee_relative = r.employee_relative_ids and True or False

    @api.ondelete(at_uninstall=False)
    def _unlink_except_group_hr_user(self):
        for r in self:
            if r.relative_employee_ids and not self.env.user.has_group('hr.group_hr_user'):
                raise UserError(_("Only users having HR Officer access rights will be able to delete the employee's relatives"))
