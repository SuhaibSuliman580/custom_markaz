from odoo import models, api, _
from odoo.exceptions import UserError


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    @api.ondelete(at_uninstall=False)
    def _unlink_if_has_payslips(self):
        """
        This override ensures no resource calendar leave will be removed if it is verified in payslips.
        If the payslip is still in draft status, the resource calendar leave will be removed and the payslip will be recompute.
        """
        to_recompute_payslips = self.env['hr.payslip'].sudo()
        leaves = self.holiday_id
        work_entries = self.env['hr.work.entry'].sudo().search([('leave_id', 'in', leaves.ids)])
        for leave in leaves:
            payslip = work_entries.filtered(lambda entry: entry.leave_id == leave).payslip_ids[:1]
            if not payslip:
                continue

            # Payslips: draft
            if not leave.payslip_status:
                to_recompute_payslips |= payslip.filtered(lambda ps: ps.state == 'draft')
                continue

            # Payslips: verified
            raise UserError(_("Could not remove the resource leave related to the time off '%s' while it is still referred"
                              " by the payslip '%s'. Please cancel the payslip first.")
                              % (leave.display_name, payslip.display_name))
        # recompute related draft payslips
        if to_recompute_payslips:
            to_recompute_payslips.compute_sheet()
