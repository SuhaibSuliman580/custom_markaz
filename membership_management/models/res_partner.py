from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ── MEMBERSHIP INFORMATION ──
    is_doctor = fields.Boolean(string='Is Doctor', default=False)
    membership_number = fields.Char(string='Membership Number', readonly=True, copy=False)
    doctor_membership_state = fields.Selection([
        ('none', 'No Membership'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('suspended', 'Suspended'),
    ], string='Membership Status', default='none', readonly=True, copy=False)
    membership_start_date = fields.Date(string='Membership Start Date', readonly=True, copy=False)
    membership_end_date = fields.Date(string='Membership End Date', readonly=True, copy=False)
    active_membership_id = fields.Many2one(
        'membership.period', string='Active Membership', readonly=True, copy=False,
    )
    membership_application_ids = fields.One2many(
        'membership.application', 'partner_id', string='Membership Applications',
    )
    membership_period_ids = fields.One2many(
        'membership.period', 'partner_id', string='Membership Periods',
    )
    membership_join_date = fields.Date(string='Membership Join Date')
    membership_rejoin_date = fields.Date(string='Re-Join Date')
    membership_rejoin_decision = fields.Char(string='Re-Join Decision Number')
    deletion_number = fields.Char(string='Deletion Number')
    branch_return_date = fields.Date(string='Branch Return Date')

    # ── Doctor Personal Info ──
    arabic_name = fields.Char(string='Name (Arabic)')
    national_id = fields.Char(string='National ID / Iqama')
    birth_date = fields.Date(string='Date of Birth')
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
    ], string='Gender')
    nationality_id = fields.Many2one('res.country', string='Nationality')
    medical_specialty_id = fields.Many2one('medical.specialty', string='Medical Specialty')
    father_name = fields.Char(string='Father Name')
    mother_name = fields.Char(string='Mother Name')
    social_status = fields.Selection([
        ('single', 'Single'),
        ('married', 'Married'),
        ('engaged', 'Engaged'),
    ], string='Social Status')
    wives_count = fields.Integer(string='Number of Wives')
    children_count = fields.Integer(string='Number of Children')
    registry_place_number = fields.Char(string='Registry Place & Number')

    # ── Medical Qualifications ──
    # medical_specialty = fields.Selection([
    #     ('general', 'General Practice'),
    #     ('internal', 'Internal Medicine'),
    #     ('surgery', 'General Surgery'),
    #     ('pediatrics', 'Pediatrics'),
    #     ('obstetrics', 'Obstetrics & Gynecology'),
    #     ('cardiology', 'Cardiology'),
    #     ('orthopedics', 'Orthopedics'),
    #     ('dermatology', 'Dermatology'),
    #     ('ophthalmology', 'Ophthalmology'),
    #     ('ent', 'ENT (Ear, Nose & Throat)'),
    #     ('neurology', 'Neurology'),
    #     ('psychiatry', 'Psychiatry'),
    #     ('radiology', 'Radiology'),
    #     ('anesthesia', 'Anesthesia'),
    #     ('pathology', 'Pathology'),
    #     ('urology', 'Urology'),
    #     ('oncology', 'Oncology'),
    #     ('dental', 'Dentistry'),
    #     ('pharmacy', 'Pharmacy'),
    #     ('other', 'Other'),
    # ], string='Medical Specialty')
    qualification = fields.Selection([
        ('bachelor', 'Bachelor (MBBS)'),
        ('master', 'Master'),
        ('md', 'MD'),
        ('phd', 'PhD / Doctorate'),
        ('fellowship', 'Fellowship'),
        ('board', 'Board Certified'),
    ], string='Highest Qualification')
    university = fields.Char(string='University / Institution')
    graduation_year = fields.Char(string='Graduation Year')

    # ── Medical License ──
    medical_license_no = fields.Char(string='Medical License Number')
    license_issue_date = fields.Date(string='License Issue Date')
    license_expiry_date = fields.Date(string='License Expiry Date')
    license_type = fields.Selection([
        ('permanent', 'Permanent'),
        ('temporary', 'Temporary'),
    ], string='License Type')
    permanent_license_date_1 = fields.Date(string='Permanent License Date 1')
    permanent_license_date_2 = fields.Date(string='Permanent License Date 2')
    temporary_license_date_1 = fields.Date(string='Temporary License Date 1')
    temporary_license_date_2 = fields.Date(string='Temporary License Date 2')
    temporary_license_date_3 = fields.Date(string='Temporary License Date 3')
    ministry_registration_number = fields.Char(
        string='Ministry of Health Registration Number'
    )

    # ── Employment ──
    workplace_name = fields.Char(string='Current Workplace')
    workplace_type = fields.Selection([
        ('government', 'Government Hospital'),
        ('private_hospital', 'Private Hospital'),
        ('clinic', 'Private Clinic'),
        ('university', 'University Hospital'),
        ('military', 'Military Hospital'),
        ('other', 'Other'),
    ], string='Workplace Type')
    years_of_experience = fields.Integer(string='Years of Experience')
    is_employee = fields.Boolean(string='Is Employee')
    fund_status = fields.Selection([
        ('contracted', 'Contracted'),
        ('not_contracted', 'Not Contracted'),
        ('blocked', 'Blocked'),
    ], string='Fund Status')
    transfer_from_entity = fields.Char(string='Transfer From Entity')
    transfer_from_date = fields.Date(string='Transfer From Date')
    transfer_to_entity = fields.Char(string='Transfer To Entity')
    transfer_to_date = fields.Date(string='Transfer To Date')
    outside_country = fields.Boolean(string='Outside Country')
    bank_account_number = fields.Char(string='Bank Account Number')
    bank_name = fields.Char(string='Bank Name')
    retirement_date = fields.Date(string='Retirement Date')
    retirement_decision_number = fields.Char(string='Retirement Decision Number')
    retirement_salary = fields.Float(string='Retirement Salary')
    death_date = fields.Date(string='Death Date')
    death_decision_number = fields.Char(string='Death Decision Number')
    social_security_registered = fields.Boolean(
        string='Registered in Social Security'
    )

    # SPECIALTY & DEGREE
    specialty_classification = fields.Selection([
        ('specialist', 'Specialist'),
        ('practitioner', 'Practitioner'),
        ('rare', 'Rare Specialty'),
    ], string='Classification')
    specialization_certificate_number = fields.Char(
        string='Specialization Certificate Number'
    )
    certificate_issue_place = fields.Selection([
        ('inside', 'Inside Country'),
        ('outside', 'Outside Country'),
    ], string='Certificate Issue Place')
    certificate_modify_date = fields.Date(string='Certificate Modify Date')
    certificate_modify_number = fields.Char(string='Certificate Modify Number')
    specialization_authority_1 = fields.Char(string='Specialization Authority 1')
    specialization_authority_2 = fields.Char(string='Specialization Authority 2')
    specialization_authority_3 = fields.Char(string='Specialization Authority 3')
    practice_location = fields.Selection([
        ('city', 'City'),
        ('rural', 'Rural'),
    ], string='Practice Location')

