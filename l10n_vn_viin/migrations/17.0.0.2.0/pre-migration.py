import json


def rename_tax(cr, xml_id, name_tax_new):
    name_tax_new_json = json.dumps({"en_US": name_tax_new})
    cr.execute(
        """
            WITH account_tax_ids AS (
                SELECT res_id
                FROM ir_model_data
                WHERE module='account' AND name like %s
            )

            UPDATE account_tax
            SET name=%s
            WHERE id IN (SELECT res_id FROM account_tax_ids)
        """, (f'%_{xml_id}', name_tax_new_json)
    )


def migrate(cr, version):
    rename_tax(cr, "tax_purchase_import_10", "10% Import VAT")
    rename_tax(cr, "tax_purchase_import_5", "5% Import VAT")
    rename_tax(cr, "tax_purchase_import_0", "0% Import VAT")
