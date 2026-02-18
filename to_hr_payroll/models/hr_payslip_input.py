from odoo import fields, models

from .browsable_object import InputLine


class HrPayslipInput(models.Model):
    _name = 'hr.payslip.input'
    _description = 'Payslip Input'
    _order = 'payslip_id, sequence'

    payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    salary_rule_id = fields.Many2one('hr.salary.rule', string='Salary Rule',
                                     domain="[('id', 'in', domain_salary_rule_ids)]",
                                     help="The salary rule that generated this payslip input.")
    domain_salary_rule_ids = fields.Many2many('hr.salary.rule', compute='_compute_domain_salary_rule_ids',
                                              compute_sudo=True)  # Avoid authorization errors for internal users when accessing the payslip
    sequence = fields.Integer(related='salary_rule_id.sequence', store=True)
    code = fields.Char(related='salary_rule_id.code', store=True)
    amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
                               "1% commission of basic salary for per product can defined in expression "
                               "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    description = fields.Char(string='Description')

    def _compute_domain_salary_rule_ids(self):
        for r in self:
            r.domain_salary_rule_ids = r.payslip_id.struct_id._get_rule_inputs()

    def get_inputline_obj(self):
        """
        Get an InputLine object for usage in salary rule python code
        @return: InputLine object
        @rtype: InputLine
        """
        inputs_dict = {}
        for r in self:
            inputs_dict[r.code] = r
        return InputLine(self.payslip_id.employee_id.id, inputs_dict, self.env)
