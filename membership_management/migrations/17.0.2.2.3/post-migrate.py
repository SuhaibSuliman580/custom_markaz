"""Remove the stale Arabic label attached to the profile draft selection.

Odoo stores translated selection labels on ir.model.fields.selection. Earlier
versions left ar_001="تحت المراجعه" on this specific value even
after the Python source label became "مسودة". This targeted, versioned migration
updates only that metadata translation and does not touch request state values.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE ir_model_fields_selection AS selection
           SET name = jsonb_set(
               COALESCE(selection.name, '{}'::jsonb),
               '{ar_001}',
               to_jsonb('مسودة'::text),
               true
           )
          FROM ir_model_fields AS field
         WHERE selection.field_id = field.id
           AND field.model = 'membership.profile.update'
           AND field.name = 'state'
           AND selection.value = 'draft'
    """)
