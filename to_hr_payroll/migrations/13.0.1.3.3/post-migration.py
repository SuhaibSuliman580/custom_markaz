from odoo import api, SUPERUSER_ID


def _set_timeoff_payslip_status(env):
    payslips = env['hr.payslip'].sudo().search([('state', 'not in', ('draft', 'cancel'))])
    if payslips:
        payslips.sudo()._set_timeoff_payslip_status()


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    _set_timeoff_payslip_status(env)
