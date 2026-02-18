import time
import logging

from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import formatLang, format_date, format_datetime

_logger = logging.getLogger(__name__)


class ReportL10nVnCommon(models.AbstractModel):
    _name = 'report.l10n_vn.common'
    _description = 'Vietnam Common Report'

    @api.model
    def _get_lines(self, data):
        raise ValidationError(_("The method '_get_lines' has NOT been implemented."))

    @api.model
    def formatLang(self, value, digits=None, grouping=True, monetary=False, dp=False, currency_obj=False):
        return formatLang(self.env, value, digits=digits, grouping=grouping, monetary=monetary, dp=dp, currency_obj=currency_obj)

    @api.model
    def format_date(self, date, pattern=False):
        return format_date(self.env, date, date_format=pattern)

    @api.model
    def format_tz(self, dt, tz=False, format=False):  # pylint: disable=redefined-builtin
        _logger.warning("`format_tz` is deprecated and will be removed soon. Please use `format_datetime` instead.")
        return self.format_datetime(dt, tz, format)

    @api.model
    def format_datetime(self, dt, tz=False, format=False):  # pylint: disable=redefined-builtin
        return format_datetime(self.env, value=dt, tz=tz, dt_format=format)

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model') or not self.env.context.get('active_id'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        model = self.env.context.get('active_model')
        doc = self.env[model].browse(self.env.context.get('active_id'))
        lines = self._get_lines(data)

        res = {
            'doc_ids': self.ids,
            'doc_model': model,
            'data': data,
            'doc': doc,
            'time': time,
            'lines': lines,
            'legal_name': '',
            'formatLang': self.formatLang,
            'format_date': self.format_date,
            'format_datetime': self.format_datetime,
            'format_tz': self.format_tz
        }
        if 'legal_name' in data:
            res['legal_name'] = data['legal_name']
        return res
