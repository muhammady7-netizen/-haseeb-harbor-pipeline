import zipfile, os

base = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\task-sources'
zip_dir = r'C:\Users\Haseeb Mirza\OneDrive\Documents\Default Project\local-qc\canonical-zips'

tasks = [
    (os.path.join(base, 'the-thread-that-outlived-its-own-start-v7'),
     os.path.join(zip_dir, 'UPLOAD-THIS-TO-QC-the-thread-that-outlived-its-own-start-v8.zip'),
     'the-thread-that-outlived-its-own-start'),
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
