# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class EduLancePortal(http.Controller):

    @http.route('/my/classes', auth='user', website=True)
    def my_classes(self, **kwargs):
        student = request.env.user.partner_id
        sessions = request.env['edu.session'].sudo().search([
            ('group_id.student_ids', 'in', student.id),
            ('status', 'in', ['scheduled', 'in_progress']),
        ], order='date_start')
        return request.render('edu_lance.portal_my_classes', {
            'sessions': sessions,
        })

    @http.route('/my/homework', auth='user', website=True)
    def my_homework(self, **kwargs):
        student = request.env.user.partner_id
        homeworks = request.env['edu.homework'].sudo().search([
            ('group_id.student_ids', 'in', student.id),
        ], order='due_date')
        return request.render('edu_lance.portal_my_homework', {
            'homeworks': homeworks,
            'student': student,
        })
