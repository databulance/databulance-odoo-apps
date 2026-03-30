# -*- coding: utf-8 -*-
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class EduGroup(models.Model):
    _name = 'edu.group'
    _description = 'Study Group'
    _inherit = ['mail.thread']
    _order = 'name'

    name = fields.Char(required=True, tracking=True)
    subject_id = fields.Many2one('edu.subject', required=True, ondelete='restrict')
    level_id = fields.Many2one('edu.level', ondelete='set null')
    teacher_id = fields.Many2one(
        'hr.employee', domain=[('x_is_teacher','=',True)],
        ondelete='set null', tracking=True,
    )
    curriculum_id = fields.Many2one(
        'edu.curriculum',
        domain="[('subject_id','=',subject_id)]",
    )
    max_students = fields.Integer(default=8)
    color = fields.Integer(default=0)
    active = fields.Boolean(default=True)
    notes = fields.Text()
    schedule_ids = fields.One2many('edu.schedule','group_id')
    session_ids = fields.One2many('edu.session','group_id')
    student_ids = fields.Many2many(
        'res.partner','edu_group_student_rel','group_id','partner_id',
        domain=[('x_is_student','=',True)],
    )
    student_count = fields.Integer(compute='_compute_counts')
    session_count = fields.Integer(compute='_compute_counts')
    occupancy = fields.Float(compute='_compute_counts')
    subscription_type_ids = fields.Many2many('edu.subscription.type')
    block_without_subscription = fields.Boolean(default=False)

    @api.depends('student_ids','session_ids','max_students')
    def _compute_counts(self):
        for rec in self:
            rec.student_count = len(rec.student_ids)
            rec.session_count = len(rec.session_ids)
            rec.occupancy = (
                rec.student_count / rec.max_students * 100
                if rec.max_students else 0.0
            )


class EduSchedule(models.Model):
    _name = 'edu.schedule'
    _description = 'Weekly Schedule'
    _order = 'group_id, day_of_week'

    group_id = fields.Many2one('edu.group', required=True, ondelete='cascade')
    day_of_week = fields.Selection(
        [('0','Mon'),('1','Tue'),('2','Wed'),('3','Thu'),
         ('4','Fri'),('5','Sat'),('6','Sun')], required=True,
    )
    time_start = fields.Float(required=True)
    time_end = fields.Float(required=True)
    active = fields.Boolean(default=True)

    @api.constrains('time_start','time_end')
    def _check_times(self):
        for rec in self:
            if rec.time_end <= rec.time_start:
                raise ValidationError('End time must be after start time.')


class EduSession(models.Model):
    _name = 'edu.session'
    _description = 'Class Session'
    _inherit = ['mail.thread']
    _order = 'date_start desc'

    name = fields.Char(compute='_compute_name', store=True)
    group_id = fields.Many2one('edu.group', required=True, ondelete='cascade')
    subject_id = fields.Many2one(related='group_id.subject_id', store=True)
    level_id = fields.Many2one(related='group_id.level_id', store=True)
    teacher_id = fields.Many2one(
        'hr.employee', related='group_id.teacher_id', store=True,
    )
    sub_teacher_id = fields.Many2one(
        'hr.employee', domain=[('x_is_teacher','=',True)], ondelete='set null',
    )
    date_start = fields.Datetime(required=True)
    date_end = fields.Datetime(required=True)
    duration = fields.Float(compute='_compute_duration', store=True)
    status = fields.Selection(
        [('scheduled','Scheduled'),('in_progress','In Progress'),
         ('done','Done'),('cancelled','Cancelled')],
        default='scheduled', tracking=True,
    )
    # Abstract video fields — populated by nexus_vr or nexus_zoom bridge
    video_url = fields.Char(copy=False, help='Set by nexus_vr or nexus_zoom.')
    video_provider = fields.Selection(
        [('bbb','BigBlueButton'),('zoom','Zoom')], copy=False,
    )
    visit_ids = fields.One2many('edu.visit','session_id')
    present_count = fields.Integer(compute='_compute_attendance')
    absent_count = fields.Integer(compute='_compute_attendance')

    @api.depends('group_id','date_start')
    def _compute_name(self):
        for rec in self:
            if rec.group_id and rec.date_start:
                rec.name = (
                    f"{rec.group_id.name} — "
                    f"{rec.date_start.strftime('%d %b %Y %H:%M')}"
                )
            else:
                rec.name = 'New Session'

    @api.depends('date_start','date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                rec.duration = (
                    rec.date_end - rec.date_start
                ).total_seconds() / 3600
            else:
                rec.duration = 0.0

    @api.depends('visit_ids.status')
    def _compute_attendance(self):
        for rec in self:
            rec.present_count = sum(
                1 for v in rec.visit_ids
                if v.status in ('present','late')
            )
            rec.absent_count = sum(
                1 for v in rec.visit_ids if v.status == 'absent'
            )

    def action_start(self):
        self.ensure_one()
        self._generate_visits()
        self.status = 'in_progress'

    def action_done(self):
        self.ensure_one()
        self._auto_mark_absent()
        self._create_earnings()
        self.status = 'done'

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def _generate_visits(self):
        existing_students = self.visit_ids.mapped('student_id')
        for student in self.group_id.student_ids:
            if student not in existing_students:
                self.env['edu.visit'].create({
                    'session_id': self.id,
                    'student_id': student.id,
                    'status': 'unmarked',
                })

    def _auto_mark_absent(self):
        self.visit_ids.filtered(
            lambda v: v.status == 'unmarked'
        ).write({'status': 'absent'})

    def _create_earnings(self):
        if not self.teacher_id:
            return
        rate = self.env['edu.teacher.rate'].search([
            ('teacher_id','=',self.teacher_id.id),
            ('subject_id','=',self.subject_id.id),
        ], limit=1)
        if not rate:
            return
        commission_rate = float(
            self.env['ir.config_parameter'].sudo().get_param(
                'edu_lance.commission_rate', '20.0'
            )
        )
        amount = rate._compute_amount(self)
        self.env['edu.teacher.earning'].create({
            'session_id': self.id,
            'teacher_id': self.teacher_id.id,
            'rate_id': rate.id,
            'amount': amount,
            'commission_rate': commission_rate,
            # FIX: net_amount is computed field, do not set it directly
        })


class EduVisit(models.Model):
    _name = 'edu.visit'
    _description = 'Attendance Record'
    _order = 'session_id, student_id'

    session_id = fields.Many2one('edu.session', required=True, ondelete='cascade', index=True)
    student_id = fields.Many2one(
        'res.partner', required=True, ondelete='cascade', index=True,
        domain=[('x_is_student','=',True)],
    )
    status = fields.Selection(
        [('unmarked','Unmarked'),('present','Present'),
         ('absent','Absent'),('late','Late'),('excused','Excused')],
        default='unmarked', required=True,
    )
    subscription_line_id = fields.Many2one('edu.subscription', ondelete='set null')
    conditionally_paid = fields.Boolean(default=False)
    notes = fields.Char()

    _sql_constraints = [
        ('visit_uniq','UNIQUE(session_id, student_id)',
         'Duplicate visit for this student and session.'),
    ]

    def write(self, vals):
        # FIX: call super first, then writeoff
        res = super().write(vals)
        if vals.get('status') in ('present','late'):
            mode = self.env['ir.config_parameter'].sudo().get_param(
                'edu_lance.writeoff_mode', 'per_visit'
            )
            if mode == 'per_visit':
                for rec in self:
                    rec._writeoff_subscription()
        return res

    def _writeoff_subscription(self):
        sub = self.student_id.active_subscription_id
        if sub and sub.lessons_remaining > 0:
            sub.lessons_remaining -= 1
            self.subscription_line_id = sub.id
        else:
            self.conditionally_paid = True
