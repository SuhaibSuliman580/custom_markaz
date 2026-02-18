from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError


class HrPayrollStructure(models.Model):
    """
    Salary structure used to defined
    - Basic
    - Allowances
    - Deductions
    """
    _name = 'hr.payroll.structure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Salary Structure'

    @tools.ormcache()
    def _default_type_id(self):
        return self.env.ref('hr_contract.structure_type_employee', raise_if_not_found=False)

    name = fields.Char(required=True, translate=True, tracking=True)
    active = fields.Boolean(string='Active', default=True)
    code = fields.Char(string='Reference', required=True, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, copy=False, tracking=True,
                                 default=lambda self: self.env.company, ondelete='cascade')
    note = fields.Text(string='Description')
    parent_id = fields.Many2one('hr.payroll.structure', string='Parent', domain="[('company_id','=',company_id)]", tracking=True)
    children_ids = fields.One2many('hr.payroll.structure', 'parent_id', string='Children', copy=True, tracking=True)
    rule_ids = fields.One2many('hr.salary.rule', 'struct_id', string='Salary Rules', copy=True, tracking=True)
    type_id = fields.Many2one('hr.payroll.structure.type', string='Structure Type', default=_default_type_id)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_('You cannot create a recursive salary structure.'))

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {}, name=_("%s (copy)") % (self.name), code=_("%s (copy)") % (self.code))
        return super(HrPayrollStructure, self).copy(default)

    def get_all_rules(self):
        """
        @return: returns a list of tuple (id, sequence) of rules that are maybe to apply
        """
        all_rules = []
        for struct in self:
            all_rules += struct.rule_ids._recursive_search_of_rules()
        return all_rules

    def _get_parent_structure(self):
        parent = self.mapped('parent_id')
        if parent:
            parent = parent._get_parent_structure()
        return parent | self

    def _get_rule_inputs(self):
        structs = self._get_parent_structure()
        rules = structs.get_all_rules()
        sorted_rule_ids = [id for id, sequence in sorted(rules, key=lambda x:x[1])]
        return self.env['hr.salary.rule'].browse(sorted_rule_ids).filtered(lambda r: r.input_salary)

    def unlink(self):
        self.with_context(active_test=False).mapped('rule_ids').unlink()
        return super(HrPayrollStructure, self).unlink()

    def toggle_active(self):
        super(HrPayrollStructure, self).toggle_active()
        self.with_context(active_test=False).mapped('rule_ids').filtered(lambda rule: rule.active != rule.struct_id.active).toggle_active()

    def action_reset_rules(self):
        """
        This method resets all the salary rules of the structures in self to the default installation values
        """
        self.rule_ids.action_reset()
