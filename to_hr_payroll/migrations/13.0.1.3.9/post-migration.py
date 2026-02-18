

def migrate(cr, version):
    cr.execute("""
    ALTER TABLE hr_contract_advantage DROP COLUMN code;
    """)
