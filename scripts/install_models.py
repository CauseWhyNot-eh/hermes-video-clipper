"""Download pinned, ungated local Whisper weights for the npm installer."""
from pathlib import Path
import sys
from huggingface_hub import snapshot_download

REVISION = '536b0662742c02347bc0e980a01041f333bce120'

if __name__ == '__main__':
    root = Path(sys.argv[1]).resolve()
    destination = root / 'assets/models/whisper-small'
    snapshot_download(repo_id='Systran/faster-whisper-small', revision=REVISION,
                      local_dir=destination, allow_patterns=['config.json', 'model.bin', 'tokenizer.json', 'vocabulary.txt', 'README.md'])
    if not all((destination / name).is_file() for name in ['model.bin', 'config.json', 'tokenizer.json', 'vocabulary.txt']):
        raise RuntimeError('Whisper download incomplete; setup is not ready')
    print('Pinned Whisper small weights ready; license: MIT')
