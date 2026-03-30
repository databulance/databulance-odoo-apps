# -*- coding: utf-8 -*-
from odoo import fields, models, api


class EduCurriculum(models.Model):
    _name = 'edu.curriculum'
    _description = 'Curriculum'
    _order = 'subject_id, level_id, name'

    name = fields.Char(required=True, translate=True)
    subject_id = fields.Many2one('edu.subject', required=True, ondelete='restrict')
    level_id = fields.Many2one('edu.level', ondelete='set null')
    description = fields.Html(translate=True)
    active = fields.Boolean(default=True)
    lesson_ids = fields.One2many('edu.lesson','curriculum_id')
    lesson_count = fields.Integer(compute='_compute_lesson_count')
    source_channel_id = fields.Many2one(
        'slide.channel', ondelete='set null', readonly=True,
        help='Source slide.channel if migrated from EduOps.',
    )

    @api.depends('lesson_ids')
    def _compute_lesson_count(self):
        for rec in self:
            rec.lesson_count = len(rec.lesson_ids)


class EduLesson(models.Model):
    _name = 'edu.lesson'
    _description = 'Lesson'
    _order = 'curriculum_id, sequence'

    name = fields.Char(required=True, translate=True)
    curriculum_id = fields.Many2one('edu.curriculum', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    content = fields.Html(translate=True, sanitize=True, sanitize_style=True)
    video_url = fields.Char()
    attachment_ids = fields.Many2many('ir.attachment')
    resource_ids = fields.Many2many('edu.resource')
    active = fields.Boolean(default=True)
    source_slide_id = fields.Many2one(
        'slide.slide', ondelete='set null', readonly=True,
    )
