from . import models
from . import report
from . import wizard

from odoo import _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import create_column, column_exists


# PRE_INIT_HOOK
def _ensure_valid_hr_contracts(env):
    contracts_of_no_job = env['hr.contract'].sudo().search([('job_id', '=', False)])
    hr_contract_admin_new = env.ref('hr_contract.hr_contract_admin_new', raise_if_not_found=False)
    # In demo mode, `hr_contract_admin_new` comes without job_id sepecified.
    # we need to exclude it to avoid installation failure
    if hr_contract_admin_new and not hr_contract_admin_new.job_id:
        contracts_of_no_job -= hr_contract_admin_new
    if contracts_of_no_job:
        this_module = env['ir.module.module'].search([('name', '=', 'to_hr_payroll')], limit=1)
        raise ValidationError(
            _(
                "The following %s contracts have no job position specified. Please specify job position"
                " for all the HR Contract before installing the module %s!\n%s"
                )
            % (
                len(contracts_of_no_job),
                this_module.shortdesc,
                "\n".join("- %s (%s)" % (c.display_name, c.employee_id.name) for c in contracts_of_no_job)
                )
            )


def _ensure_no_hr_payroll_installed(env):
    """
    This method ensures the Odoo EE's hr_payroll module is not installed before installing this to_hr_payroll
    """
    hr_payroll_module = env['ir.module.module'].search([('name', '=', 'hr_payroll'), ('state', '=', 'installed')], limit=1)
    if hr_payroll_module:
        to_hr_payroll_module = env['ir.module.module'].search([('name', '=', 'to_hr_payroll')], limit=1)
        raise UserError(_("You must uninstall the module %s (%s) before you could install the module %s (%s).")
                        % (hr_payroll_module.shortdesc, hr_payroll_module.name, to_hr_payroll_module.shortdesc, to_hr_payroll_module.name))


def _backup_children_column(env):
    """ Save old values of `children` column to another temp column
    """
    if not column_exists(env.cr, 'hr_employee', 'temp_children'):
        create_column(env.cr, 'hr_employee', 'temp_children', 'integer')
    env.cr.execute("UPDATE hr_employee SET temp_children = children;")


# POST_INIT_HOOK
def _generate_salary_structures(env):
    companies = env['res.company'].search([])
    if companies:
        companies._generate_salary_structures()


def _generate_salary_slip_sequences(env):
    companies = env['res.company'].search([])
    if companies:
        companies._generate_salary_slip_sequences()


def _restore_children_column(env):
    """ Restore `children` values from `temp_children`, then drop the temp column
    """
    env.cr.execute("UPDATE hr_employee SET children = temp_children, total_dependant = temp_children;")
    env.cr.execute("ALTER TABLE hr_employee DROP COLUMN temp_children;")


def _set_default_companies_cycle(env):
    cycle = env.ref('to_hr_payroll.hr_salary_cycle_default')
    env['res.company'].search([]).write({
        'salary_cycle_id': cycle.id
        })


def _compute_contract_personal_tax_rule(env):
    contracts = env['hr.contract'].search([('personal_tax_rule_id', '=', False)])
    if contracts:
        contracts._compute_tax_rule()


def _compute_contract_salary_structure(env):
    contracts = env['hr.contract'].search([('struct_id', '=', False)])
    if contracts:
        contracts._compute_structure()


# INIT HOOKS
def pre_init_hook(env):
    _ensure_no_hr_payroll_installed(env)
    _ensure_valid_hr_contracts(env)
    _backup_children_column(env)


def post_init_hook(env):
    _generate_salary_structures(env)
    _generate_salary_slip_sequences(env)
    _restore_children_column(env)
    _set_default_companies_cycle(env)
    _compute_contract_personal_tax_rule(env)
    _compute_contract_salary_structure(env)
