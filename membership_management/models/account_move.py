from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, _
import logging

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    membership_activated = fields.Boolean(
        string='Membership Activated', default=False, copy=False,
        help='Technical field to prevent double activation.',
    )

    def write(self, vals):
        res = super().write(vals)
        # Trigger on payment_state change
        if vals.get('payment_state') in ('paid', 'in_payment'):
            for move in self:
                if move.move_type == 'out_invoice' and not move.membership_activated:
                    move._activate_membership_if_applicable()
        return res

    @api.model
    def _cron_activate_paid_memberships(self):
        """Fallback cron: find paid invoices linked to applications that weren't activated."""
        applications = self.env['membership.application'].search([
            ('state', '=', 'approved'),
            ('membership_period_id', '=', False),
            ('invoice_id', '!=', False),
        ])
        for app in applications:
            invoice = app.invoice_id
            if invoice.payment_state in ('paid', 'in_payment') and not invoice.membership_activated:
                try:
                    invoice._activate_membership_if_applicable()
                    _logger.info("Cron activated membership for invoice %s", invoice.id)
                except Exception as e:
                    _logger.error("Cron membership activation error for invoice %s: %s", invoice.id, e)

    def _activate_membership_if_applicable(self):
        """Activate membership when the linked invoice is paid."""
        self.ensure_one()

        # Skip if already activated
        if self.membership_activated:
            return

        Application = self.env['membership.application']
        Period = self.env['membership.period']

        # --- Case 1: New membership from application ---
        application = Application.search([
            ('invoice_id', '=', self.id),
            ('state', '=', 'approved'),
            ('membership_period_id', '=', False),
        ], limit=1)

        if application:
            today = fields.Date.today()
            membership_number = self.env['ir.sequence'].next_by_code('membership.number')
            period = Period.create({
                'name': membership_number,
                'partner_id': application.partner_id.id,
                'start_date': today,
                'end_date': today + relativedelta(years=1),
                'state': 'active',
                'invoice_id': self.id,
                'application_id': application.id,
            })
            period._generate_qr_code()

            application.write({'membership_period_id': period.id})

            application.partner_id.write({
                'doctor_membership_state': 'active',
                'membership_number': membership_number,
                'membership_start_date': today,
                'membership_end_date': today + relativedelta(years=1),
                'active_membership_id': period.id,
            })

            # Mark as activated to prevent double execution
            self.with_context(skip_membership_check=True).write({
                'membership_activated': True,
            })

            _logger.info("Membership activated for partner %s: %s",
                         application.partner_id.id, membership_number)
            return

        # --- Case 2: Renewal payment ---
        renewal_period = Period.search([
            ('invoice_id', '=', self.id),
            ('state', 'in', ('active', 'expired')),
        ], limit=1)

        if renewal_period:
            today = fields.Date.today()
            if renewal_period.state == 'active' and renewal_period.end_date >= today:
                new_start = renewal_period.end_date
            else:
                new_start = today

            new_end = new_start + relativedelta(years=1)

            renewal_period.write({
                'start_date': new_start if renewal_period.state == 'expired' else renewal_period.start_date,
                'end_date': new_end,
                'state': 'active',
            })
            renewal_period._generate_qr_code()

            renewal_period.partner_id.write({
                'doctor_membership_state': 'active',
                'membership_start_date': renewal_period.start_date,
                'membership_end_date': new_end,
                'active_membership_id': renewal_period.id,
            })

            self.with_context(skip_membership_check=True).write({
                'membership_activated': True,
            })


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        """Override payment creation to trigger membership activation."""
        res = super().action_create_payments()

        # After payment is created, check linked invoices
        if self.line_ids:
            invoices = self.line_ids.mapped('move_id').filtered(
                lambda m: m.move_type == 'out_invoice'
            )
            for invoice in invoices:
                # Refresh to get updated payment_state
                invoice.invalidate_recordset(['payment_state'])
                if invoice.payment_state in ('paid', 'in_payment') and not invoice.membership_activated:
                    try:
                        invoice._activate_membership_if_applicable()
                    except Exception as e:
                        _logger.warning("Membership activation after payment error: %s", e)

        return res
