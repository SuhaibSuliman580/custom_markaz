from odoo import api, SUPERUSER_ID


def _fill_salary_rule_for_payslip_input(env):
    payslip_inputs = env['hr.payslip.input'].sudo().search([('salary_rule_id', '=', False)])
    for slip in payslip_inputs.mapped('payslip_id'):
        all_rule_inputs = slip.struct_id._get_rule_inputs()
        for payslip_input in payslip_inputs.filtered(lambda inp: inp.payslip_id == slip):
            rule_inputs = all_rule_inputs.filtered(lambda rinp: rinp.code == payslip_input.code)
            if rule_inputs:
                payslip_input.write({
                    'salary_rule_id': rule_inputs[0].salary_rule_id.id
                    })


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _fill_salary_rule_for_payslip_input(env)
