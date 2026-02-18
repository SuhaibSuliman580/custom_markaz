from odoo import fields, models, _
from odoo.exceptions import UserError
from datetime import datetime, time


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    payslip_ids = fields.Many2many('hr.payslip', 'hr_payslip_work_entry_rel', 'work_entry_id', 'payslip_id',
                                   string='Paylips', help="Technical field")

    def write(self, vals):
        if vals.keys() & self._get_fields_sync_payslip():
            self._check_sync_payslip()
        res = super(HrWorkEntry, self).write(vals)
        # Re-compute
        payslips_draft = self.payslip_ids.filtered(lambda r: r.state == 'draft')
        payslips_draft.compute_sheet()
        return res

    def unlink(self):
        self._check_sync_payslip()
        payslips_draft = self.payslip_ids.filtered(lambda r: r.state == 'draft')
        res = super(HrWorkEntry, self).unlink()
        # Re-compute
        payslips_draft.compute_sheet()
        return res

    def _get_fields_sync_payslip(self):
        return {'employee_id', 'date_start', 'date_stop', 'work_entry_type_id', 'state', 'active'}

    def _check_sync_payslip(self):
        payslips_verified = self.payslip_ids.filtered(lambda r: r.state in ('verify', 'done'))
        if payslips_verified:
            for we in (self & payslips_verified.work_entry_ids):
                we_msg = "%s (%s - %s)" % (we.name, we.date_start, we.date_stop)
                payslip_msg = ", ".join(payslips_verified.mapped('name'))
                raise UserError(_("This action will make edit/delete Work Entry `%s` calculated in payslip in verified/done status. "
                          "Please check related payslips:\n"
                          "%s") % (we_msg, payslip_msg))

    def _cron_validate_work_entry(self):
        start_today = datetime.combine(fields.Date.today(), time.min)
        self.search([
            ('date_stop', '<', start_today),
            ('state', '=', 'draft'),
        ]).action_validate()
