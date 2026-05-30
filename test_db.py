import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.config import get_settings
import uuid
import json

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        try:
            tid = '00000000-0000-0000-0000-000000000000'
            res = await conn.execute(
                text("""
                    INSERT INTO invite_templates (
                        tenant_id, event_id, name, template_type, ticket_class,
                        width_px, height_px, orientation,
                        background_url, background_color, quick_style,
                        is_default, metadata, created_by
                    ) VALUES (
                        :tid, :eid, :name, CAST(:ttype AS template_type), CAST(:tc AS ticket_class),
                        :w, :h, :orient,
                        :bg_url, :bg_color, :qstyle::jsonb,
                        :is_default, :meta::jsonb, :uid
                    )
                    RETURNING *
                """),
                {
                    'tid': tid, 'eid': None, 'name': 'Test',
                    'ttype': 'designed', 'tc': 'vip', 'w': 1000, 'h': 1000,
                    'orient': 'portrait', 'bg_url': None, 'bg_color': '#fff',
                    'qstyle': '{}', 'is_default': False, 'meta': '{}', 'uid': tid
                }
            )
            print('Insert succeeded!')
            await conn.rollback()
        except Exception as e:
            print('DB ERROR:', type(e).__name__, getattr(e, 'orig', e))

asyncio.run(main())
