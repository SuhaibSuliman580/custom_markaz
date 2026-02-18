from odoo import models, fields


class HRDepartment(models.Model):
    _inherit = 'hr.department'

    department_register_partner_ids = fields.One2many(
        'hr.department.register.partner', 'department_id',
        string='Department Register Partner',
        groups='to_hr_payroll.group_hr_payroll_user',
        help="If set value, The partner will record on Journal Items, "
        "related to the corresponding contribution register")

    def _get_contribution_register_partner(self, contribution_register):
        """
        @param contribution_register: hr.contribution.register record
        """
        register_partner = self.department_register_partner_ids.filtered(
            lambda r: r.contribution_register_id.id == contribution_register.id
            ).partner_id[:1]
        if register_partner or not self.parent_id:
            return register_partner
        else:
            return self.parent_id._get_contribution_register_partner(contribution_register) \
                or contribution_register.partner_id
