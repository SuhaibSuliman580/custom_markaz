def migrate(cr, version):
    """
    Ensure company's payslips_auto_generation_day will not be less than 1
    """
    cr.execute("""
    SELECT column_name
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'res_company' and column_name = 'payslips_auto_generation_day'
    """)
    if cr.fetchone():
        cr.execute("""
        UPDATE res_company SET payslips_auto_generation_day = 1 WHERE payslips_auto_generation_day < 1;
        """)
