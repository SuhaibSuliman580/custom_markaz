
def migrate(cr, version):
    cr.execute("""
        ALTER TABLE hr_meal_order_line DROP COLUMN IF EXISTS ordered_by;
        ALTER TABLE hr_meal_order_line DROP COLUMN IF EXISTS date_ordered;
        ALTER TABLE hr_meal_order_line DROP COLUMN IF EXISTS scheduled_date;
        ALTER TABLE hr_meal_order_line DROP COLUMN IF EXISTS scheduled_hour;
        ALTER TABLE hr_meal_order_line DROP COLUMN IF EXISTS approved_by;
        ALTER TABLE hr_meal_order_line DROP COLUMN IF EXISTS date_approved;
    """)
