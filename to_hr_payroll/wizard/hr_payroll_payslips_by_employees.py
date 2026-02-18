from markupsafe import Markup
from odoo import fields, api, models, _
from odoo.exceptions import UserError


class HrPayslipEmployees(models.TransientModel):
    _name = 'hr.payslip.employees'
    _description = 'Generate payslips for all selected employees'

    batch_id = fields.Many2one('hr.payslip.run', string='Payslip Batch', required=True, ondelete='cascade')
    mode = fields.Selection([
        ('batch_period', 'Payslip Batch Period'),
        ('contract_period', 'Contract Validity')], string='Generation Mode', required=True, default='batch_period',
        help="* Payslip Batch Period: all the generated payslips will have the same period as the batch's;\n"
        "* Contract Validity: generated paysplips will have their period constrained by their corresponding contracts")
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_group_rel', 'payslip_id', 'employee_id', 'Employees')

    @api.model
    def default_get(self, fields_list):
        data = super(HrPayslipEmployees, self).default_get(fields_list)
        active_id = self.env.context.get('active_id')
        data['batch_id'] = active_id
        return data

    def _prepare_payslip_data(self):
        self.ensure_one()
        vals_list = []
        payslip_batch = self.batch_id
        ignore_employees = self.env['hr.employee']
        for employee in self.with_context(active_test=False).employee_ids:
            include_trial_contracts = self.env['hr.payslip']._include_trial_contracts(
                payslip_batch.thirteen_month_pay,
                payslip_batch.thirteen_month_pay_include_trial
            )
            contracts = employee.with_context(
                include_trial_contracts=include_trial_contracts
                )._get_contracts(payslip_batch.date_start, payslip_batch.date_end, states=['open', 'close'])
            if contracts:
                contracts = contracts.sorted('date_start')
                # we get only the last contract of the year when working on 13-month batch
                # so that there will be ONLY one slip for a single employee
                if payslip_batch.thirteen_month_pay and payslip_batch.thirteen_month_pay_year > 1970:
                    contracts = contracts[-1]
            else:
                ignore_employees |= employee
                continue

            contract_group = {}
            for contract in contracts:
                dict_hash = contract._get_group_hashcode_for_payslip_consolidation()
                contract_group.setdefault(dict_hash, contract)
                contract_group[dict_hash] |= contract
            if len(contract_group.items()) == 1:
                # start preparing payslip data base on the batch's mode
                if self.mode == 'batch_period':
                    slip_data = {
                        'name': self.env['hr.payslip'].with_context(
                            thirteen_month_pay=payslip_batch.thirteen_month_pay,
                            thirteen_month_pay_year=payslip_batch.thirteen_month_pay_year
                            )._get_salary_slip_name(employee, payslip_batch.date_end),
                        'company_id': employee.company_id.id,
                        'salary_cycle_id': payslip_batch.salary_cycle_id.id or self.env.company.salary_cycle_id.id,
                        'employee_id': employee.id,
                        'payslip_run_id': payslip_batch.id,
                        'date_from': payslip_batch.date_start,
                        'date_to': payslip_batch.date_end,
                        'credit_note': payslip_batch.credit_note,
                        'thirteen_month_pay': payslip_batch.thirteen_month_pay,
                        'thirteen_month_pay_year': payslip_batch.thirteen_month_pay_year,
                        'thirteen_month_pay_include_trial': payslip_batch.thirteen_month_pay_include_trial
                        }
                    vals_list.append(slip_data)
                else:
                    slip_data = contracts.with_context(
                        payslip_run_id=payslip_batch.id,
                        credit_note=payslip_batch.credit_note,
                        thirteen_month_pay=payslip_batch.thirteen_month_pay,
                        thirteen_month_pay_year=payslip_batch.thirteen_month_pay_year,
                        thirteen_month_pay_include_trial=payslip_batch.thirteen_month_pay_include_trial,
                        salary_cycle_id=payslip_batch.salary_cycle_id or self.env.company.salary_cycle_id,
                        )._prepare_payslip_data(payslip_batch.date_start, payslip_batch.date_end)
                    if not bool(slip_data):
                        continue
                    vals_list.append(slip_data)
            else:
                for __, group_contracts in contract_group.items():
                    if len(group_contracts) > 1:
                        if contracts.filtered(lambda r: r.date_start > group_contracts[0].date_end
                                              and r.date_start < group_contracts[-1].date_start):
                            for contract in group_contracts:
                                slip_data = contract.with_context(
                                    payslip_run_id=payslip_batch.id,
                                    credit_note=payslip_batch.credit_note,
                                    thirteen_month_pay_year=payslip_batch.thirteen_month_pay_year,
                                    salary_cycle_id=payslip_batch.salary_cycle_id or self.env.company.salary_cycle_id,
                                    )._prepare_payslip_data(payslip_batch.date_start, payslip_batch.date_end)
                                vals_list.append(slip_data)
                            continue
                    slip_data = group_contracts.with_context(
                        payslip_run_id=payslip_batch.id,
                        credit_note=payslip_batch.credit_note,
                        thirteen_month_pay_year=payslip_batch.thirteen_month_pay_year,
                        salary_cycle_id=payslip_batch.salary_cycle_id or self.env.company.salary_cycle_id,
                        )._prepare_payslip_data(payslip_batch.date_start, payslip_batch.date_end)
                    vals_list.append(slip_data)
        if ignore_employees:
            body = _("Payslips for the following employees were not generated due to no corresponding"
                     " contracts that match the payslip batch's period were found:<br />%s."
                     ) % ", ".join(ignore_employees.mapped('name'))
            if payslip_batch.thirteen_month_pay and not payslip_batch.thirteen_month_pay_include_trial:
                body += _("<br />You may want to enable '13th-Month Pay Incl. Trial' for the"
                          " payslip batch to include trial contracts during payslip generation.")
            payslip_batch.message_post(body=Markup(body))
        return vals_list

    def compute_sheet(self):
        vals_list = []
        for r in self:
            if not r.employee_ids:
                raise UserError(_("You must select employee(s) to generate payslip(s)."))
            vals_list += r._prepare_payslip_data()
        if vals_list:
            payslips = self.env['hr.payslip'].create(vals_list)
            payslips.with_context(do_not_recompute_fields=True).compute_sheet()
        return {'type': 'ir.actions.act_window_close'}
