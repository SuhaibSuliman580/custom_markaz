from odoo import models, _
from odoo.exceptions import UserError


class IrModule(models.Model):
    _inherit = 'ir.module.module'

    def button_immediate_install(self):
        if 'hr_payroll' in self.mapped('name'):
            raise UserError(_("You must uninstall the module `to_hr_payroll` before you could install the module `hr_payroll`."))
        return super(IrModule, self).button_immediate_install()
