import zipfile, os

tasks = [
    (r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\thread\the-thread-that-outlived-its-own-start',
     r'C:\Users\Haseeb Mirza\Documents\Default Project\UPLOAD-THIS-TO-QC-the-thread-v7.zip',
     'the-thread-that-outlived-its-own-start'),
    (r'C:\Users\HASEEB~1\AppData\Local\Temp\opencode\answer\the-answer-she-already-gave',
     r'C:\Users\Haseeb Mirza\Documents\Default Project\UPLOAD-THIS-TO-QC-the-answer-v7.zip',
     'the-answer-she-already-gave'),
]

exclude_dirs = {'__pycache__', '.git', '.pytest_cache'}
exclude_exts = {'.pyc', '.swp', '.swo', '.orig', '.rej'}

for src, zip_path, prefix in tasks:
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            for f in files:
                ext = os.path.splitext(f)[1]
                if ext in exclude_exts:
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, src)
                arc = prefix + '/' + rel.replace(os.sep, '/')
                zf.writestr(arc, open(full, 'rb').read())
    print(f'{prefix}: {os.path.getsize(zip_path)} bytes')
