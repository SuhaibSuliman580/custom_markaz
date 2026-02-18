from odoo import api, SUPERUSER_ID


def _update_contract_advantage_action(env):
    env.ref('to_hr_payroll.update_contract_advantage_action').binding_model_id = False


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_contract_advantage_action(env)
