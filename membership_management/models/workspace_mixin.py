from datetime import datetime, time, timedelta

import pytz

from odoo import fields, models, _


class MembershipWorkspaceMixin(models.AbstractModel):
    _name = 'membership.workspace.mixin'
    _description = 'Membership Workspace Framework Mixin'

    def _workspace_company_domain(self, field_name='company_id'):
        return [(field_name, 'in', self.env.companies.ids)]

    def _workspace_today_bounds_utc(self):
        today = fields.Date.context_today(self)
        user_tz = pytz.timezone(self.env.user.tz or 'UTC')
        start_local = user_tz.localize(datetime.combine(today, time.min))
        stop_local = user_tz.localize(datetime.combine(today + timedelta(days=1), time.min))
        return (
            start_local.astimezone(pytz.UTC).replace(tzinfo=None),
            stop_local.astimezone(pytz.UTC).replace(tzinfo=None),
        )

    def _workspace_action(self, model, name, domain=None, view_mode='tree,form', context=None):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'view_mode': view_mode,
            'domain': domain or [],
            'context': context or {},
            'target': 'current',
        }

    def _workspace_service_request_action(self, name, domain=None, context=None):
        action = self.env.ref('membership_management.action_membership_service_request').read()[0]
        action['name'] = name
        action['domain'] = self._workspace_company_domain() + (domain or [])
        action['context'] = context or {}
        return action

    def _workspace_invoice_action(self, name, domain=None, context=None):
        return self._workspace_action(
            'account.move',
            name,
            self._workspace_company_domain() + [
                ('move_type', '=', 'out_invoice'),
                ('membership_service_request_id', '!=', False),
            ] + (domain or []),
            context=context,
        )

    def _workspace_revenue_ledger_action(self, name, domain=None, context=None):
        action = self.env.ref(
            'syndicate_revenue_distribution.action_revenue_distribution_ledger_line'
        ).read()[0]
        action['name'] = name
        action['domain'] = self._workspace_company_domain() + (domain or [])
        action['context'] = context or {}
        return action

    def _workspace_open_record(self, name, model, record):
        return {
            'type': 'ir.actions.act_window',
            'name': name,
            'res_model': model,
            'res_id': record.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _workspace_action_label(self, count, singular, plural):
        return singular if count == 1 else plural
