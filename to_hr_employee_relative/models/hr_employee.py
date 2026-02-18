from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    relative_ids = fields.One2many('hr.employee.relative', 'employee_id', string='Related')
    # Override marital field to add compute
    marital = fields.Selection(compute='_compute_marital', store=True, readonly=False)
    # Override spouse_complete_name field
    spouse_complete_name = fields.Char(string="Spouse Complete Name", groups="hr.group_hr_user", tracking=True,
                                       compute='_compute_spouse_name', readonly=False, store=True)
    other_dependant = fields.Integer(string='Other Dependant', compute='_compute_dependant', store=True,
                                     tracking=True, groups="hr.group_hr_user",
                                     help="Number of other people that are dependent on this employee.")
    total_dependant = fields.Integer(string='Total Dependant', compute='_compute_dependant', store=True, tracking=True, groups="hr.group_hr_user",
                                     help="Total number of people that are dependent on this employee.")
    # Override children field
    children = fields.Integer(compute='_compute_dependant', store=True, groups='hr.group_hr_user')

    @api.depends('relative_ids', 'relative_ids.type')
    def _compute_marital(self):
        for r in self:
            if any(relative.type in ('wife', 'husband') for relative in r.relative_ids):
                r.marital = 'married'
            else:
                r.marital = r.marital

    @api.depends('relative_ids', 'marital')
    def _compute_spouse_name(self):
        for r in self:
            spouse = r.relative_ids.filtered(lambda rel: rel.type in ('wife', 'husband'))[:1]
            if r.marital in ('married', 'cohabitant'):
                if spouse:
                    r.spouse_complete_name = spouse.contact_id.name
                else:
                    r.spouse_complete_name = r._origin.spouse_complete_name
            else:
                r.spouse_complete_name = False

    @api.constrains('relative_ids')
    def _check_marital_partner(self):
        for r in self:
            if r.relative_ids and all(type in r.relative_ids.mapped('type') for type in ['wife', 'husband']):
                raise UserError(_("The employee %(name)s can not have both husband and wife at the same time.",
                                  name=r.name
                                  ))

    @api.depends('relative_ids', 'relative_ids.is_dependant', 'relative_ids.type')
    def _compute_dependant(self):
        for r in self:
            dependant = r.relative_ids.filtered(lambda rel: rel.is_dependant)
            children_dependant = dependant.filtered(lambda dep: dep.type == 'children')
            other_dependant = dependant - children_dependant
            r.total_dependant = len(dependant)
            r.children = len(children_dependant)
            r.other_dependant = len(other_dependant)
