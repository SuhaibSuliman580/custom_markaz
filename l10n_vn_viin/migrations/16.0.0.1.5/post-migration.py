from odoo import SUPERUSER_ID, api


def _update_account_vat_exemption_tax_for_sale(env):
    """
    Why need this migration
    1. First of all in previous version (< 16.0.0.1.4) we unintentionally set wrong
    'minus_report_expression_ids' and 'plus_report_expression_ids' for account_tax_template of VAT Exemption for tax type Sale
    Which will cause tax generation have wrong tag_ids (account_tag), and lead to wrong account_tag
    assign to journal items for both invoice and refund. This is why when viewing the Tax Report in menu Report
    The value of VAT exemption tax for sale itself and value of goods are missmatch between each other
    2. This migration attempt to update account tax for VAT Exemption for tax type Sale
    First we are going to find the the VAT Exemption for tax type Sale (account.tax)
    we also need VAT exemption Tax Type Sale Template (account.tax.template)
    then update journal items (account_move_line) of Out invoice, out receipt, out refund because
    those might take incorrect account_tag (tax_tag_ids) which already got from the wrong Tax above
    """
    c200_tax_template = env.ref('l10n_vn_viin.account_tax_template_sale_vat_exemption', raise_if_not_found=False)
    c133_tax_template = env.ref('l10n_vn_viin.tax_sale_vat_exemption', raise_if_not_found=False)
    coa_vns = env['account.chart.template']._get_installed_vietnam_coa_templates()
    vn_companies = env['res.company'].search([('chart_template_id', 'in', coa_vns.ids)])
    old_invoice_account_tag = env['account.account.tag'].with_context(active_test=False).search([
            ('name', '=like', '+Exemption Output VAT'),
            ('country_id', '=', env.ref('base.vn').id),
            ('applicability', '=', 'taxes')
    ], limit=1)
    new_invoice_account_tag = env['account.account.tag'].with_context(active_test=False).search([
        ('name', '=like', '+Untaxed Sales of Goods & Services taxed VAT Exemption'),
        ('country_id', '=', env.ref('base.vn').id),
        ('applicability', '=', 'taxes')
    ], limit=1)
    old_refund_account_tag = env['account.account.tag'].with_context(active_test=False).search([
            ('name', '=like', '-Exemption Output VAT'),
            ('country_id', '=', env.ref('base.vn').id),
            ('applicability', '=', 'taxes')
    ], limit=1)
    new_refund_account_tag = env['account.account.tag'].with_context(active_test=False).search([
        ('name', '=like', '-Untaxed Sales of Goods & Services taxed VAT Exemption'),
        ('country_id', '=', env.ref('base.vn').id),
        ('applicability', '=', 'taxes')
    ], limit=1)
    for r in vn_companies:
        tax_template = False
        if r.chart_template_id == env.ref('l10n_vn_viin.vn_template_c133'):
            tax_template = c133_tax_template
            tax_sale_vat_exemption_xml_id = 'l10n_vn_viin.%s_tax_sale_vat_exemption' % r.id
        elif r.chart_template_id == env.ref('l10n_vn.vn_template'):
            tax_template = c200_tax_template
            tax_sale_vat_exemption_xml_id = 'l10n_vn_viin.%s_account_tax_template_sale_vat_exemption' % r.id
        if tax_template:
            tax_sale_vat_exemption = env.ref(tax_sale_vat_exemption_xml_id, raise_if_not_found=False)
            if tax_sale_vat_exemption:
                # Update account_tax for invoice case for tax_sale_vat_exemption and related account_move_line
                if old_invoice_account_tag and new_invoice_account_tag not in tax_sale_vat_exemption.invoice_repartition_line_ids.tag_ids:
                    tax_sale_vat_exemption.invoice_repartition_line_ids.filtered(
                        lambda line: line.tag_ids
                    )[:1].write({'tag_ids': [(6, 0, new_invoice_account_tag.ids)]})
                    _update_journal_items_for_vat_exemption_tax(
                        env, tax_sale_vat_exemption, old_invoice_account_tag, new_invoice_account_tag, r
                    )
                # Update account_tax for refund case for tax_sale_vat_exemption and related account_move_line
                if old_refund_account_tag and new_refund_account_tag not in tax_sale_vat_exemption.refund_repartition_line_ids.tag_ids:
                    tax_sale_vat_exemption.refund_repartition_line_ids.filtered(
                        lambda line: line.tag_ids
                    )[:1].write({'tag_ids': [(6, 0, new_refund_account_tag.ids)]})
                    _update_journal_items_for_vat_exemption_tax(
                        env, tax_sale_vat_exemption, old_refund_account_tag, new_refund_account_tag, r
                    )


def _update_journal_items_for_vat_exemption_tax(env, account_tax, old_account_tag, new_account_tag, company):
    query = f"""
        UPDATE account_account_tag_account_move_line_rel aml_tag_rel
            SET account_account_tag_id = {new_account_tag.id}
        FROM account_move_line aml
        JOIN account_move_line_account_tax_rel aml_tax_rel on aml_tax_rel.account_move_line_id = aml.id
        WHERE aml.id = aml_tag_rel.account_move_line_id and
            aml_tax_rel.account_tax_id = {account_tax.id} and
            aml_tag_rel.account_account_tag_id = {old_account_tag.id} and
            aml.company_id = {company.id}
    """
    env.cr.execute(query)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _update_account_vat_exemption_tax_for_sale(env)
