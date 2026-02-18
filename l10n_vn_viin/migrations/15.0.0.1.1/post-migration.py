from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    report_paperformat_portrait = env.ref('l10n_vn_viin.report_paperformat_template_paperformat_portrait', False)
    report_paperformat_landscape = env.ref('l10n_vn_viin.report_paperformat_template_paperformat_landscape', False)
    if report_paperformat_portrait:
        report_paperformat_portrait.margin_bottom = 25
    if report_paperformat_landscape:
        report_paperformat_landscape.margin_bottom = 25
