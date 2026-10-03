"""Project-local clip catalogue. No clipping or uploading is implied."""
from pathlib import Path
from contextlib import contextmanager
import hashlib
import math
import sqlite3
from datetime import datetime, timezone

class Catalog:
    def __init__(self, database):
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript('''
                CREATE TABLE IF NOT EXISTS sources (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    speaker TEXT NOT NULL,
                    input_path TEXT NOT NULL,
                    rights_confirmed INTEGER NOT NULL,
                    ranked INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS clips (
                    id TEXT PRIMARY KEY,
                    source_id TEXT NOT NULL REFERENCES sources(id),
                    title TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    score REAL NOT NULL,
                    start_s REAL NOT NULL,
                    end_s REAL NOT NULL,
                    video_path TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'candidate',
                    final_path TEXT,
                    music_id TEXT
                );
                CREATE TABLE IF NOT EXISTS music_uses (
                    clip_id TEXT PRIMARY KEY REFERENCES clips(id),
                    music_id TEXT NOT NULL,
                    used_at TEXT NOT NULL
                );
            ''')

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.database, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute('PRAGMA foreign_keys=ON')
        try:
            connection.execute('BEGIN IMMEDIATE')
            with connection:
                yield connection
        finally:
            connection.close()

    def add_source(self, media, name, origin, speaker='', rights_confirmed=False):
        media = Path(media).resolve()
        if not media.is_file():
            raise ValueError('Source file does not exist')
        if not name.strip() or not origin.strip():
            raise ValueError('Source name and origin are required')
        source_id = 'S-' + hashlib.sha256(str(media).encode()).hexdigest()[:12]
        with self.connect() as connection:
            existing = connection.execute('SELECT * FROM sources WHERE input_path=?', (str(media),)).fetchone()
            if existing:
                source_id = existing['id']
                if existing['name'] != name or existing['origin'] != origin:
                    raise ValueError('Source already registered with different metadata; preserve it')
                if rights_confirmed and not existing['rights_confirmed']:
                    connection.execute('UPDATE sources SET rights_confirmed=1 WHERE id=?', (source_id,))
                return source_id
            connection.execute('INSERT INTO sources(id,name,origin,speaker,input_path,rights_confirmed) VALUES(?,?,?,?,?,?)',
                               (source_id, name, origin, speaker, str(media), int(rights_confirmed)))
        return source_id

    def relocate_source(self, source_id, media):
        """Relocate identical source bytes without changing IDs, rights or clip history."""
        media = Path(media).resolve()
        if not media.is_file():
            raise ValueError('Relocated source file does not exist')
        with self.connect() as connection:
            source = connection.execute('SELECT * FROM sources WHERE id=?', (source_id,)).fetchone()
            if not source:
                raise ValueError('Unknown source')
            original = Path(source['input_path'])
            if not original.is_file():
                raise ValueError('Original source must exist for identical-content verification')
            with original.open('rb') as old, media.open('rb') as new:
                if hashlib.file_digest(old, 'sha256').digest() != hashlib.file_digest(new, 'sha256').digest():
                    raise ValueError('Relocated source must have identical content')
            conflict = connection.execute('SELECT id FROM sources WHERE input_path=? AND id!=?',
                                          (str(media), source_id)).fetchone()
            if conflict:
                raise ValueError('Relocated path belongs to another source')
            connection.execute('UPDATE sources SET input_path=? WHERE id=?', (str(media), source_id))
        return source_id

    def sources(self):
        with self.connect() as connection:
            return [dict(row) for row in connection.execute('SELECT * FROM sources ORDER BY id')]

    def import_clips(self, source_id, candidates, reviewed=False):
        if not reviewed:
            raise ValueError('Inspect context, captions and framing before importing reviewed candidates')
        if not isinstance(candidates, list) or not candidates:
            raise ValueError('A non-empty candidate list is required')
        with self.connect() as connection:
            source = connection.execute('SELECT * FROM sources WHERE id=?', (source_id,)).fetchone()
            if not source:
                raise ValueError('Unknown source')
            if not source['rights_confirmed']:
                raise ValueError('Source reuse rights have not been confirmed')
            if source['ranked']:
                raise ValueError('Source already ranked; do not silently replace its clip library')
            clip_ids = []
            for candidate in candidates:
                title = candidate['title'].strip()
                topic = candidate['topic'].strip()
                score = float(candidate['score'])
                start, end = float(candidate['start_s']), float(candidate['end_s'])
                path = Path(candidate['video_path']).resolve()
                if not title or not topic or not all(math.isfinite(v) for v in (score, start, end)):
                    raise ValueError('Title/topic and finite score/bounds are required')
                if start < 0 or end <= start or not path.is_file():
                    raise ValueError('Invalid bounds or missing exported clip file')
                clip_id = 'C-' + hashlib.sha256(f'{source_id}:{start:.6f}:{end:.6f}'.encode()).hexdigest()[:12]
                values = (clip_id, source_id, title, topic, score, start, end, str(path))
                existing = connection.execute('SELECT * FROM clips WHERE id=?', (clip_id,)).fetchone()
                if existing:
                    stored = tuple(existing[key] for key in ('id','source_id','title','topic','score','start_s','end_s','video_path'))
                    if stored != values:
                        raise ValueError('Duplicate clip bounds with conflicting data; preserve existing clip')
                else:
                    connection.execute('INSERT INTO clips(id,source_id,title,topic,score,start_s,end_s,video_path) VALUES(?,?,?,?,?,?,?,?)', values)
                clip_ids.append(clip_id)
            return clip_ids

    def keep_top_half(self, source_id):
        with self.connect() as connection:
            source = connection.execute('SELECT * FROM sources WHERE id=?', (source_id,)).fetchone()
            if not source:
                raise ValueError('Unknown source')
            if source['ranked']:
                return connection.execute("SELECT count(*) FROM clips WHERE source_id=? AND status!='not_kept'", (source_id,)).fetchone()[0]
            candidates = connection.execute("SELECT id FROM clips WHERE source_id=? AND status='candidate' ORDER BY score DESC,start_s,id", (source_id,)).fetchall()
            if not candidates:
                raise ValueError('No reviewed candidates; source preparation is not complete')
            keep = math.ceil(len(candidates) / 2)
            for index, row in enumerate(candidates):
                connection.execute('UPDATE clips SET status=? WHERE id=?', ('ready' if index < keep else 'not_kept', row['id']))
            connection.execute('UPDATE sources SET ranked=1 WHERE id=?', (source_id,))
            return keep

    def choices(self, per_source=5, internal=False):
        if not isinstance(per_source, int) or per_source < 1:
            raise ValueError('per_source must be a positive integer')
        with self.connect() as connection:
            rows = connection.execute("SELECT c.*,s.name AS source_name,s.origin,s.speaker FROM clips c JOIN sources s ON s.id=c.source_id WHERE c.status='ready' ORDER BY s.id,c.score DESC,c.start_s,c.id").fetchall()
            counts, choices = {}, []
            for row in rows:
                if counts.get(row['source_id'], 0) >= per_source:
                    continue
                counts[row['source_id']] = counts.get(row['source_id'], 0) + 1
                if internal:
                    choices.append(dict(row))
                else:
                    origin = ' — '.join(part for part in (row['source_name'], row['speaker'], row['origin']) if part)
                    choices.append({'name': row['title'], 'topic': row['topic'], 'duration_seconds': round(row['end_s']-row['start_s'],3), 'source': origin})
            return choices

    def select(self, clip_ids):
        if not clip_ids or len(set(clip_ids)) != len(clip_ids):
            raise ValueError('Select distinct clip IDs')
        with self.connect() as connection:
            for clip_id in clip_ids:
                row = connection.execute('SELECT status FROM clips WHERE id=?', (clip_id,)).fetchone()
                if not row or row['status'] != 'ready':
                    raise ValueError('Only an available clip can be selected')
                connection.execute("UPDATE clips SET status='selected' WHERE id=?", (clip_id,))
        return list(clip_ids)

    def mark_finished(self, clip_id, final_path, music_id):
        final = Path(final_path).resolve()
        if not final.is_file() or not music_id.strip():
            raise ValueError('An existing final file and a music ID are required')
        with self.connect() as connection:
            clip = connection.execute('SELECT * FROM clips WHERE id=?', (clip_id,)).fetchone()
            if clip and clip['status'] == 'finished' and clip['final_path'] == str(final) and clip['music_id'] == music_id:
                return clip_id
            if not clip or clip['status'] != 'selected':
                raise ValueError('Finish only a user-selected clip')
            if final == Path(clip['video_path']).resolve():
                raise ValueError('Keep the original export separate from the finished file')
            connection.execute("UPDATE clips SET status='finished',final_path=?,music_id=? WHERE id=?", (str(final),music_id,clip_id))
            connection.execute('INSERT INTO music_uses(clip_id,music_id,used_at) VALUES(?,?,?)', (clip_id,music_id,datetime.now(timezone.utc).isoformat()))
        return clip_id

    def recent_music(self, limit=10):
        if not isinstance(limit, int) or limit < 1:
            raise ValueError('limit must be positive')
        with self.connect() as connection:
            return [row['music_id'] for row in connection.execute('SELECT music_id FROM music_uses ORDER BY used_at DESC,clip_id LIMIT ?', (limit,))]

    def status(self):
        with self.connect() as connection:
            counts = {row['status']: row['amount'] for row in connection.execute('SELECT status,count(*) AS amount FROM clips GROUP BY status')}
            return {'sources':connection.execute('SELECT count(*) FROM sources').fetchone()[0], 'clips':counts,
                    'music_uses':connection.execute('SELECT count(*) FROM music_uses').fetchone()[0]}


def media_info(path):
    import json
    import shutil
    import subprocess
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Media file does not exist')
    program = shutil.which('ffprobe')
    if not program:
        raise ValueError('ffprobe is required; run doctor')
    result = subprocess.run([program,'-v','error','-show_entries','format=duration:stream=codec_type,width,height',
                             '-of','json',str(path)], capture_output=True, text=True, timeout=30)
    if result.returncode:
        raise ValueError('Not a decodable video: ' + result.stderr.strip()[:240])
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    if not any(stream.get('codec_type') == 'video' and stream.get('width',0)>0 for stream in streams):
        raise ValueError('A real video stream is required')
    if not any(stream.get('codec_type') == 'audio' for stream in streams):
        raise ValueError('Speaker audio is missing')
    duration = float(data.get('format', {}).get('duration', 0))
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('A positive media duration is required')
    return {'duration_seconds':duration,'streams':streams}


def music_tracks(root):
    import json
    manifest = root / 'assets' / 'music' / 'manifest.json'
    if not manifest.is_file():
        return []
    tracks = json.loads(manifest.read_text(encoding='utf-8')).get('tracks', [])
    for track in tracks:
        for field in ('path','attribution_file'):
            candidate = (root / track[field]).resolve()
            if not candidate.is_relative_to(root.resolve()) or not candidate.is_file():
                raise ValueError('Music manifest contains a missing or non-project file')
        if track['license'] not in ('CC BY 3.0','CC BY 4.0'):
            raise ValueError('A music license requires review before use')
        digest = hashlib.sha256((root / track['path']).read_bytes()).hexdigest()
        if digest != track['sha256']:
            raise ValueError('Music integrity check failed: ' + track['title'])
    if len({track['sha256'] for track in tracks}) != len(tracks):
        raise ValueError('Duplicate audio in the music bank')
    return tracks


def doctor(root):
    import json
    import shutil
    channel_path = root / 'config' / 'channel.json'
    channel = json.loads(channel_path.read_text(encoding='utf-8')) if channel_path.is_file() else {}
    ai = channel.get('ai', {})
    delivery = channel.get('delivery', {})

    tracks = music_tracks(root)
    tools = {name:shutil.which(name) for name in ('ffmpeg','ffprobe','node','uv')}

    blockers = []
    automatic_blockers = []
    if channel.get('preparation_tool') != 'custom_agent_led':
        automatic_blockers.append('Custom clipping pipeline is not selected')
    else:
        automatic_blockers.append('Agent editorial/framing review is required; unattended active-speaker selection is not implemented')
    if ai.get('provider') != 'builder_session' and ai.get('api_key_status') != 'verified':
        automatic_blockers.append('LLM key and actual clip-selection inference are not verified')
    if not tools['ffmpeg'] or not tools['ffprobe']:
        blockers.append('FFmpeg/FFprobe are required')
    if delivery.get('mode') != 'local_files':
        blockers.append('YouTube authentication/uploader and actual unlisted visibility are not verified')
    blockers.append('Watermark asset/handle and important-word highlighting need approval/validation')
    return {'project_root':str(root),'catalogue_helper_ready':True,'music_tracks_verified':len(tracks),
            'tools':tools,'blockers':blockers,'delivery_mode':delivery.get('mode', 'unlisted_upload'),
            'ai_provider':ai.get('provider'), 'workflow_mode':channel.get('workflow_mode'),
            'automatic_clipping_blockers':automatic_blockers}


def main(argv=None):
    import argparse
    import json
    import sys
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=root/'.workflow'/'catalog.sqlite3')
    commands = parser.add_subparsers(dest='command',required=True)
    for name in ('doctor','status','sources','recent-music'):
        commands.add_parser(name)
    add = commands.add_parser('add-source')
    add.add_argument('file',type=Path)
    add.add_argument('--name',required=True)
    add.add_argument('--origin',required=True)
    add.add_argument('--speaker',default='')
    add.add_argument('--rights-confirmed',action='store_true')
    ingest = commands.add_parser('import-clips')
    ingest.add_argument('manifest',type=Path)
    ingest.add_argument('--source',required=True)
    ingest.add_argument('--reviewed',action='store_true')
    rank = commands.add_parser('rank')
    rank.add_argument('--source',required=True)
    listing = commands.add_parser('list')
    listing.add_argument('--per-source',type=int,default=5)
    listing.add_argument('--internal',action='store_true')
    select = commands.add_parser('select')
    select.add_argument('--clip',action='append',required=True)
    finish = commands.add_parser('mark-finished')
    finish.add_argument('--clip',required=True)
    finish.add_argument('--file',type=Path,required=True)
    finish.add_argument('--music',required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'doctor':
            output = doctor(root)
        else:
            catalog = Catalog(args.db)
            if args.command == 'status':
                output = catalog.status()
            elif args.command == 'sources':
                output = catalog.sources()
            elif args.command == 'add-source':
                media_info(args.file)
                output = {'source_id':catalog.add_source(args.file,args.name,args.origin,args.speaker,args.rights_confirmed)}
            elif args.command == 'import-clips':
                payload = json.loads(args.manifest.read_text(encoding='utf-8'))
                candidates = payload.get('clips') if isinstance(payload,dict) else payload
                if not isinstance(candidates,list) or not candidates:
                    raise ValueError('Manifest must contain a non-empty clips list')
                for candidate in candidates:
                    candidate['video_path'] = str((root/Path(candidate['video_path'])).resolve())
                    info = media_info(candidate['video_path'])
                    expected = float(candidate['end_s'])-float(candidate['start_s'])
                    if abs(info['duration_seconds']-expected)>0.75:
                        raise ValueError('Export duration differs from supplied source bounds')
                output = {'clip_ids':catalog.import_clips(args.source,candidates,args.reviewed)}
            elif args.command == 'rank':
                output = {'kept':catalog.keep_top_half(args.source)}
            elif args.command == 'list':
                output = catalog.choices(args.per_source,args.internal)
            elif args.command == 'select':
                output = {'selected':catalog.select(args.clip)}
            elif args.command == 'recent-music':
                output = catalog.recent_music()
            elif args.command == 'mark-finished':
                if args.music not in {track['id'] for track in music_tracks(root)}:
                    raise ValueError('Choose a track ID from the project music manifest')
                media_info(args.file)
                output = {'finished':catalog.mark_finished(args.clip,args.file,args.music)}
        print(json.dumps(output,ensure_ascii=False,indent=2))
        return 0
    except (ValueError,KeyError,TypeError,OSError,sqlite3.Error) as error:
        print(json.dumps({'error':str(error)},ensure_ascii=False))
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
