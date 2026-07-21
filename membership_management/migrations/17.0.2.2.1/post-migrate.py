"""Stabilize request sources after the Phase 1 user-interface rollout.

Approved requests are immutable audit records and retain their stored source.
Every other legacy request is corrected deterministically from request_type.
"""


def migrate(cr, version):
    cr.execute("""
        UPDATE membership_profile_update
           SET source = CASE request_type
               WHEN 'onboard_existing_member'
                   THEN 'manual_existing_member_onboarding'
               ELSE 'manual_profile_completion'
           END
         WHERE state != 'approved'
           AND source IS DISTINCT FROM CASE request_type
               WHEN 'onboard_existing_member'
                   THEN 'manual_existing_member_onboarding'
               ELSE 'manual_profile_completion'
           END
    """)
