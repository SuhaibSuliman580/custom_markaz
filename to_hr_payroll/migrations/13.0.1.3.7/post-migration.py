def migrate(cr, version):
    _delete_messages(cr)


def _delete_messages(cr):
    cr.execute("""
    DELETE FROM mail_message
    WHERE model = 'hr.payslip.line';
    DELETE FROM mail_followers
    WHERE res_model = 'hr.payslip.line';
    """)
