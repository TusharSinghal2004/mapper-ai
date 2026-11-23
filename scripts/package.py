"""Create a portable source download using an explicit safe file list."""
import pathlib, zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

def main():
    files = [ROOT / name for name in ('README.md', 'requirements.txt', 'requirements-lock.txt', '.env.example', '.gitignore', 'vercel.json', 'start-local.cmd', 'skills-lock.json')]
    files += [p for folder in ('dist', 'scripts', 'data') for p in (ROOT / folder).rglob('*')
              if p.is_file() and p.name != 'source.zip' and '__pycache__' not in p.parts
              and not p.name.startswith('.env') and p.suffix in ('.py', '.mjs', '.html', '.css', '.js', '.json', '.csv', '.xlsx', '.md', '.svg', '.png', '.jpg', '.webp', '.ico', '.gif')]
    files += list((ROOT/'.agents/skills/composio').rglob('*.md'))
    with zipfile.ZipFile(ROOT / 'dist/source.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            if path.exists(): archive.write(path, path.relative_to(ROOT))
    print('Packaged source. Local secrets and installed packages excluded.')

if __name__ == '__main__': main()
