# -*- coding: utf-8 -*-
import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class EduMigrationWizard(models.TransientModel):
    _name = 'edu.migration.wizard'
    _description = 'Import from EduOps'

    dry_run = fields.Boolean(default=True, string='Dry Run (preview only)')
    migrate_levels = fields.Boolean(default=True)
    migrate_subjects = fields.Boolean(default=True)
    migrate_curriculum = fields.Boolean(default=True)
    migrate_wallet = fields.Boolean(default=True)
    migrate_resources = fields.Boolean(default=True)
    result_log = fields.Text(readonly=True)

    def action_run(self):
        log = []
        if self.migrate_levels:
            log += self._migrate_levels()
        if self.migrate_subjects:
            log += self._migrate_subjects()
        if self.migrate_curriculum:
            log += self._migrate_curriculum()
        if self.migrate_wallet:
            log += self._migrate_wallet()
        if self.migrate_resources:
            log += self._migrate_resources()
        self.result_log = '\n'.join(log)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'edu.migration.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _migrate_levels(self):
        log = ['=== Levels ===']
        for model_name in ['nexus.level', 'slide.channel.tag']:
            if model_name in self.env:
                records = self.env[model_name].sudo().search([])
                for r in records:
                    name = r.name
                    if not self.env['edu.level'].search([('name','=',name)], limit=1):
                        log.append(f'  [NEW] {name}')
                        if not self.dry_run:
                            self.env['edu.level'].create({'name': name})
                    else:
                        log.append(f'  [SKIP] {name}')
                return log
        log.append('  No level source found')
        return log

    def _migrate_subjects(self):
        log = ['=== Subjects ===']
        for model_name in ['nexus.subject']:
            if model_name in self.env:
                for r in self.env[model_name].sudo().search([]):
                    if not self.env['edu.subject'].search([('name','=',r.name)], limit=1):
                        log.append(f'  [NEW] {r.name}')
                        if not self.dry_run:
                            self.env['edu.subject'].create({'name': r.name})
                    else:
                        log.append(f'  [SKIP] {r.name}')
                return log
        log.append('  nexus.subject not found')
        return log

    def _migrate_curriculum(self):
        log = ['=== Curriculum ===']
        channels = self.env['slide.channel'].sudo().search([('active','=',True)])
        log.append(f'  Found {len(channels)} channels')
        default_subject = self.env['edu.subject'].search([], limit=1)
        default_level = self.env['edu.level'].search([], limit=1)
        for ch in channels:
            if self.env['edu.curriculum'].search([('source_channel_id','=',ch.id)], limit=1):
                log.append(f'  [SKIP] {ch.name}')
                continue
            log.append(f'  [NEW] {ch.name} ({len(ch.slide_ids)} lessons)')
            if not self.dry_run:
                cur = self.env['edu.curriculum'].create({
                    'name': ch.name,
                    'subject_id': default_subject.id,
                    'level_id': default_level.id if default_level else False,
                    'source_channel_id': ch.id,
                })
                for slide in ch.slide_ids.sorted('sequence'):
                    self.env['edu.lesson'].create({
                        'name': slide.name,
                        'curriculum_id': cur.id,
                        'sequence': slide.sequence,
                        'content': getattr(slide, 'html_content', '') or '',
                        'video_url': getattr(slide, 'url', False) or False,
                        'source_slide_id': slide.id,
                    })
        return log

    def _migrate_wallet(self):
        log = ['=== Wallet ===']
        model_name = next(
            (m for m in ['nexus.credit'] if m in self.env),
            None
        )
        if not model_name:
            log.append('  No wallet model found')
            return log
        records = self.env[model_name].sudo().search([])
        log.append(f'  Found {len(records)} records')
        if not self.dry_run:
            default_type = self.env['edu.subscription.type'].search([], limit=1)
            for rec in records:
                partner = getattr(rec, 'partner_id', None)
                credits = int(getattr(rec, 'credits', 0) or getattr(rec, 'balance', 0))
                if partner and credits > 0:
                    self.env['edu.subscription'].create({
                        'student_id': partner.id,
                        'type_id': default_type.id,
                        'lessons_remaining': credits,
                        'notes': 'Migrated from nexus_wallet',
                    })
                    partner.x_is_student = True
        return log

    def _migrate_resources(self):
        log = ['=== Resources ===']
        model_name = next(
            (m for m in ['nexus.resource'] if m in self.env),
            None
        )
        if not model_name:
            log.append('  nexus_resource_bank not found')
            return log
        records = self.env[model_name].sudo().search([])
        log.append(f'  Found {len(records)} resources')
        if not self.dry_run:
            for rec in records:
                self.env['edu.resource'].create({
                    'name': rec.name,
                    'resource_type': 'file',
                    'source_resource_id': rec.id,
                })
        return log
