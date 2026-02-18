from odoo import fields, models


class HrPayrollStructureType(models.Model):
    _name = 'hr.payroll.structure.type'
    _inherit = ['hr.payroll.structure.type', 'mail.thread', 'mail.activity.mixin']
    _description = 'Salary Structure Type'

    def _default_regular_struct_id(self):
        return self.env['hr.payroll.structure'].search([
            ('company_id', '=', self.env.company.id),
            ('code', '=', 'BASE')], limit=1)

    # Override `name` field
    name = fields.Char(string='Name', tracking=True, required=True)

    property_regular_struct_id = fields.Many2one('hr.payroll.structure', string='Regular Salary Structure',
        tracking=True, company_dependent=True,
        domain="[('company_id', '=', current_company_id), ('type_id','=', id)]",
        help="The salary structure that will be used as a default one for regular salary computation (e.g. for monthly payslips).")
    property_thirteen_month_struct_id = fields.Many2one('hr.payroll.structure', string='13th-Month Salary Structure',
        tracking=True, company_dependent=True,
        domain="[('company_id', '=', current_company_id), ('type_id','=', id)]",
        help='The default 13th-Month Salary Structure that will be filled as default value for 13th-Month Salary Structure field on the HR contract document')
    struct_ids = fields.One2many('hr.payroll.structure', 'type_id', string='Salary Structures')
    default_resource_calendar_id = fields.Many2one(
        company_dependent=True,
        domain="[('company_id', '=', current_company_id)]")
