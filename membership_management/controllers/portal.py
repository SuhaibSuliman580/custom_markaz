import base64

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class MembershipPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'membership_count' in counters:
            values['membership_count'] = max(
                request.env['membership.application'].sudo().search_count([
                    ('partner_id', '=', request.env.user.partner_id.id),
                ]), 1)
        return values

    # ── Dashboard ──
    @http.route('/my/membership', type='http', auth='user', website=True)
    def portal_my_membership(self, **kwargs):
        partner = request.env.user.partner_id
        applications = request.env['membership.application'].sudo().search([
            ('partner_id', '=', partner.id),
        ], order='create_date desc')
        values = {
            'partner': partner,
            'applications': applications,
            'page_name': 'membership',
        }
        return request.render('membership_management.portal_my_membership', values)

    # ── New Application Form ──
    @http.route('/my/membership/application/new', type='http', auth='user', website=True)
    def portal_membership_application_new(self, **kwargs):
        partner = request.env.user.partner_id
        Partner = request.env['res.partner']

        # Get selection field options dynamically from the model
        # specialty_field = Partner._fields['medical_specialty']
        qualification_field = Partner._fields['qualification']
        workplace_type_field = Partner._fields['workplace_type']

        values = {
            'partner': partner,
            'countries': request.env['res.country'].sudo().search([], order='name'),
            'specialties': request.env['medical.specialty'].sudo().search([]),
            'qualifications': qualification_field.selection,
            'workplace_types': workplace_type_field.selection,
            'page_name': 'membership_application_new',
        }
        return request.render('membership_management.portal_membership_application_new', values)

    # ── Submit Application ──
    @http.route('/my/membership/application/submit', type='http', auth='user',
                website=True, methods=['POST'], csrf=True)
    def portal_membership_application_submit(self, **kwargs):
        partner = request.env.user.partner_id

        # Build partner update values
        partner_vals = {
            'is_doctor': True,
            'name': kwargs.get('full_name') or partner.name,
            'arabic_name': kwargs.get('arabic_name') or '',
            'national_id': kwargs.get('national_id') or '',
            'gender': kwargs.get('gender') or False,
            'email': kwargs.get('email') or partner.email,
            'phone': kwargs.get('phone') or '',
            'qualification': kwargs.get('qualification') or False,
            'university': kwargs.get('university') or '',
            'graduation_year': kwargs.get('graduation_year') or '',
            'medical_license_no': kwargs.get('medical_license_no') or '',
            'workplace_name': kwargs.get('workplace_name') or '',
            'workplace_type': kwargs.get('workplace_type') or False,
            # ── New personal fields ──
            'father_name': kwargs.get('father_name') or '',
            'mother_name': kwargs.get('mother_name') or '',
            'social_status': kwargs.get('social_status') or False,
            'wives_count': int(kwargs.get('wives_count', 0) or 0),
            'children_count': int(kwargs.get('children_count', 0) or 0),
            'registry_place_number': kwargs.get('registry_place_number') or '',
            # ── New medical registration fields ──
            'ministry_registration_number': kwargs.get('ministry_registration_number') or '',
            'membership_number': kwargs.get('membership_number') or partner.membership_number or '',
            # ── New medical practice fields ──
            'practice_location': kwargs.get('practice_location') or False,
            'specialty_classification': kwargs.get('specialty_classification') or False,
            'specialization_certificate_number': kwargs.get('specialization_certificate_number') or '',
            'certificate_issue_place': kwargs.get('certificate_issue_place') or False,
            'is_employee': kwargs.get('is_employee') == 'on',
            'outside_country': kwargs.get('outside_country') == 'on',
            'bank_account_number': kwargs.get('bank_account_number') or '',
            'bank_name': kwargs.get('bank_name') or '',
            'social_security_registered': kwargs.get('social_security_registered') == 'on',
        }

        # Date fields
        for field in ['birth_date', 'license_issue_date', 'license_expiry_date']:
            val = kwargs.get(field)
            if val:
                partner_vals[field] = val

        # Integer field
        exp = kwargs.get('years_of_experience')
        if exp:
            try:
                partner_vals['years_of_experience'] = int(exp)
            except (ValueError, TypeError):
                pass

        # Nationality
        nat = kwargs.get('nationality_id')
        if nat:
            try:
                partner_vals['nationality_id'] = int(nat)
            except (ValueError, TypeError):
                pass

        spec = kwargs.get('medical_specialty')
        if spec:
            try:
                partner_vals['medical_specialty_id'] = int(spec)
            except (ValueError, TypeError):
                pass
        partner.sudo().write(partner_vals)

        # Create application
        application = request.env['membership.application'].sudo().create({
            'partner_id': partner.id,
            'notes': kwargs.get('notes') or '',
            'state': 'draft',
        })

        # Handle document uploads
        doc_fields = {
            'doc_national_id': 'National ID',
            'doc_license': 'Medical License',
            'doc_degree': 'Degree Certificate',
            'doc_photo': 'Personal Photo',
            'doc_other': 'Other Document',
        }
        for field_name, label in doc_fields.items():
            files = request.httprequest.files.getlist(field_name)
            for f in files:
                if f and f.filename:
                    file_data = f.read()
                    request.env['ir.attachment'].sudo().create({
                        'name': '%s - %s' % (label, f.filename),
                        'datas': base64.b64encode(file_data),
                        'res_model': 'membership.application',
                        'res_id': application.id,
                    })

        return request.redirect('/my/membership')

    # ── Application Detail ──
    @http.route('/my/membership/application/<int:application_id>', type='http',
                auth='user', website=True)
    def portal_membership_application_detail(self, application_id, **kwargs):
        partner = request.env.user.partner_id
        application = request.env['membership.application'].sudo().search([
            ('id', '=', application_id),
            ('partner_id', '=', partner.id),
        ], limit=1)
        if not application:
            return request.redirect('/my/membership')

        values = {
            'application': application,
            'page_name': 'membership_application_detail',
        }
        return request.render(
            'membership_management.portal_membership_application_detail', values
        )

    # ── Respond to Need Info ──
    @http.route('/my/membership/application/<int:application_id>/respond', type='http',
                auth='user', website=True, methods=['POST'], csrf=True)
    def portal_membership_application_respond(self, application_id, **kwargs):
        partner = request.env.user.partner_id
        application = request.env['membership.application'].sudo().search([
            ('id', '=', application_id),
            ('partner_id', '=', partner.id),
            ('state', '=', 'need_info'),
        ], limit=1)
        if not application:
            return request.redirect('/my/membership')

        notes = kwargs.get('notes', '')
        existing_notes = application.notes or ''
        updated_notes = "%s\n\n--- Doctor Response ---\n%s" % (existing_notes, notes) if existing_notes else notes
        application.write({
            'notes': updated_notes,
            'state': 'draft',
        })

        # Handle file attachment
        attachment_file = request.httprequest.files.get('attachment')
        if attachment_file and attachment_file.filename:
            file_data = attachment_file.read()
            request.env['ir.attachment'].sudo().create({
                'name': attachment_file.filename,
                'datas': base64.b64encode(file_data),
                'res_model': 'membership.application',
                'res_id': application.id,
            })

        return request.redirect('/my/membership/application/%s' % application_id)

    # ── Download Membership Card ──
    @http.route('/my/membership/card', type='http', auth='user', website=True)
    def portal_membership_card(self, **kwargs):
        partner = request.env.user.partner_id
        if partner.doctor_membership_state != 'active' or not partner.active_membership_id:
            return request.redirect('/my/membership')

        period = partner.active_membership_id
        pdf_content, _ = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            'membership_management.action_report_membership_card',
            res_ids=[period.id],
        )
        headers = [
            ('Content-Type', 'application/pdf'),
            ('Content-Disposition', 'attachment; filename=membership_card_%s.pdf' % period.name),
            ('Content-Length', len(pdf_content)),
        ]
        return request.make_response(pdf_content, headers=headers)

    # ── Invoices redirect ──
    @http.route('/my/membership/invoice', type='http', auth='user', website=True)
    def portal_membership_invoice(self, **kwargs):
        return request.redirect('/my/invoices')
