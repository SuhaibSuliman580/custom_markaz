def migrate(cr, version):
    """Bind legacy unbound evidence attachments to their single DCR request."""
    cr.execute("""
        UPDATE ir_attachment AS attachment
           SET res_model = 'membership.profile.update',
               res_id = relation.request_id
          FROM membership_profile_update_evidence_rel AS relation
         WHERE relation.attachment_id = attachment.id
           AND COALESCE(attachment.res_id, 0) = 0
           AND (
               attachment.res_model IS NULL
               OR attachment.res_model = ''
               OR attachment.res_model = 'membership.profile.update'
           )
           AND NOT EXISTS (
               SELECT 1
                 FROM membership_profile_update_evidence_rel AS other
                WHERE other.attachment_id = attachment.id
                  AND other.request_id != relation.request_id
           )
    """)
