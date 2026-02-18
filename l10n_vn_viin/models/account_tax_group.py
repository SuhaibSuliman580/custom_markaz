from odoo import models


class AccountTaxGroup(models.Model):
    _inherit = 'account.tax.group'

    def _set_tax_group_is_vat_vietnam(self, tax_group_data):
        tax_group_xml_ids = [
            'tax_group_0',
            'tax_group_5',
            'tax_group_8',
            'tax_group_10',
            'tax_group_exemption',
        ]
        for xml_id, value in tax_group_data.items():
            if xml_id in tax_group_xml_ids:
                value.update({'is_vat': True})
