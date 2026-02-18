from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # remove group contract admin off the group payroll user
    group_hr_contract_manager = env.ref('hr_contract.group_hr_contract_manager')
    group_hr_payroll_user = env.ref('to_hr_payroll.group_hr_payroll_user')
    group_hr_payroll_user.write({
        'implied_ids': [(3, group_hr_contract_manager.id)]
        })

    # remove the users who only have payroll users access rights from accessing contracts
    all_users = env['res.users'].with_context(active_test=False).search([])
    payroll_users = all_users.filtered(
        lambda u: u.has_group('to_hr_payroll.group_hr_payroll_user')
        and not u.has_group('to_hr_payroll.group_hr_payroll_manager')
        and u.has_group('hr_contract.group_hr_contract_manager')
        )
    if payroll_users:
        group_hr_contract_manager.write({
            'users': [(3, uid) for uid in payroll_users.ids]
            })
