"""Read-only storage report for the agent's mandatory post-delivery cleanup question."""
import argparse
import json
from pathlib import Path


def report(job_path):
    job_path = Path(job_path).resolve()
    job = json.loads(job_path.read_text(encoding='utf-8'))
    root = Path(job['root']).resolve()
    if not job_path.is_relative_to(root / 'library/manifests/clipping'):
        raise ValueError('Job must be inside the project clipping manifest directory')
    source = Path(job['source']['path']).resolve()
    shared_jobs = []
    for other in (root / 'library/manifests/clipping').glob('*/job.json'):
        data = json.loads(other.read_text(encoding='utf-8'))
        other_source = Path(data['source']['path']).resolve()
        if other.resolve() != job_path and (data['source']['sha256'] == job['source']['sha256']
                                           or other_source.is_relative_to(job_path.parent)):
            shared_jobs.append(str(other.relative_to(root)))
    files = [p for p in job_path.parent.rglob('*') if p.is_file()]
    return {
        'job': str(job_path.relative_to(root)),
        'work_files': len(files), 'work_bytes': sum(p.stat().st_size for p in files),
        'source': str(source), 'source_exists': source.is_file(),
        'source_bytes': source.stat().st_size if source.is_file() else 0,
        'other_jobs_using_source': shared_jobs,
        'question_required_after_each_finished_clip': True,
        'deletion_authorized': False,
        'protected': ['output/final', 'assets/music', 'inputs/music', 'assets/models', 'workflow code'],
        'warning': 'Source/transcript deletion can prevent extras and revisions. Get explicit scope approval; this command deletes nothing.'
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('job')
    print(json.dumps(report(parser.parse_args().job), indent=2))
