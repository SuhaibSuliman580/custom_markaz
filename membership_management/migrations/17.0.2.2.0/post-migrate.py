"""Preserve existing profile-update requests after Phase 1 schema changes.

The previous company_id was a stored related column, so its database values
already exist. This migration only fills missing values defensively and gives
legacy rows the explicit update-existing type/source and a supported state.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE membership_profile_update AS request
           SET company_id = partner.company_id
          FROM res_partner AS partner
         WHERE request.partner_id = partner.id
           AND request.company_id IS NULL
    """)
    cr.execute("""
        UPDATE membership_profile_update
           SET request_type = 'update_existing'
         WHERE request_type IS NULL
    """)
    cr.execute("""
        UPDATE membership_profile_update
           SET source = 'manual_profile_completion'
         WHERE source IS NULL
    """)
    cr.execute("""
        UPDATE membership_profile_update
           SET state = CASE
               WHEN state = 'need_info' THEN 'returned'
               WHEN state = 'rejected' THEN 'cancelled'
               ELSE state
           END
         WHERE state IN ('need_info', 'rejected')
    """)
