from odoo import models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _get_membership_allowed_cash_journals(self):
        journal_ids = self.env.context.get('allowed_cash_journal_ids')
        journals = self.env['account.journal'].browse(journal_ids or [])
        if not journals and self.env.user.has_group('membership_management.group_membership_service_cashier'):
            journals = self.env.user.allowed_cash_journal_ids
        return journals.filtered(lambda journal: journal.type == 'cash' and journal.company_id in self.env.companies)

    def _get_batch_available_journals(self, batch_result):
        journals = super()._get_batch_available_journals(batch_result)
        if self.env.context.get('membership_service_cashier_payment') or self.env.user.has_group('membership_management.group_membership_service_cashier'):
            allowed_journals = self._get_membership_allowed_cash_journals()
            journals = journals & allowed_journals
        return journals

    def action_create_payments(self):
        dashboard_payment = self.env.context.get('membership_service_cashier_payment')
        cashier_payment = (
            dashboard_payment
            or self.env.user.has_group('membership_management.group_membership_service_cashier')
        )
        if cashier_payment:
            allowed_journals = self._get_membership_allowed_cash_journals()
            for wizard in self:
                if wizard.journal_id not in allowed_journals:
                    raise UserError(_('لا يمكنك تسجيل قبض من دفتر يومية نقدية غير مخصص لك.'))
        if dashboard_payment:
            self = self.with_context(dont_redirect_to_payments=True)
        result = super().action_create_payments()
        if dashboard_payment:
            return self.env['membership.cashier.dashboard'].action_open_dashboard()
        return result
