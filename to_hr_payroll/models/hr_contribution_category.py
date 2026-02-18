from odoo import models, fields


class HRContributionCategory(models.Model):
    _name = 'hr.contribution.category'
    _description = 'HR Contribution Category'

    name = fields.Char(string='Name', required=True, translate=True)
    color = fields.Integer(string='Color Index')
    partner_required = fields.Boolean(string='Partner Required',
                                      help="If checked, contribution registers of this category will require a partner specified during payslip computation.")
    register_ids = fields.One2many('hr.contribution.register', 'category_id', string='Contribution Registers')
    payslip_line_ids = fields.One2many('hr.payslip.line', 'register_category_id', string='HR Payslip Lines')
    payslip_line_count = fields.Integer(string='Payslip Lines Count', compute='_compute_payslip_line_count')

    def _compute_payslip_line_count(self):
        payslips_data = self.env['hr.payslip']._read_group([('register_category_id', 'in', self.ids)], ['register_category_id'], ['__count'])
        mapped_data = {register_category.id: count for register_category, count in payslips_data}
        for r in self:
            r.payslip_line_count = mapped_data.get(r.id, 0)
