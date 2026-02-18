from odoo import models, fields, _
from odoo.exceptions import UserError


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    # override
    unpaid = fields.Boolean(tracking=True)

    def _get_payslip_protected_fields(self):
        """
        Return a dict of protected fields (field -> label) that are protected from modification
        if the time of type is stilled referred by a payslip

        @return: dict (field_1 -> label_1, field_2 -> label_2, ..., field_n -> label_n)
        """
        return {
            'unpaid': _("Unpaid"),
            }

    def write(self, vals):
        protected_fields = self._get_payslip_protected_fields()
        for field, label in protected_fields.items():
            if field in vals:
                payslips = self.env['hr.payslip'].search([('work_entry_ids.leave_id.holiday_status_id', 'in', self.ids)])
                for r in self:
                    if getattr(r, field) == vals[field]:
                        continue
                    payslip = payslips.filtered(lambda ps: ps.work_entry_ids.leave_id.holiday_status_id == r)[:1]
                    if payslip:
                        raise UserError(_("You may not be able to modify the value of the field \"%s\" of the Time Off Type \"%s\" while it is still"
                                          " referred by the payslip \"%s\".\nInstead, you could either delete the payslip or define a new Time Off Type.")
                                          % (label, r.name, payslip.name)
                                          )
        return super(HrLeaveType, self).write(vals)
