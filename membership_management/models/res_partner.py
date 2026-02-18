from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
