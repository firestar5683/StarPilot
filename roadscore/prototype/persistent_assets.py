"""Reconnect a replaced checkout to previously provisioned event assets."""
import argparse
from pathlib import Path


def restore_links(root, data=Path('/data')):
    root, data = Path(root), Path(data)
    assets, state = data / 'roadscore-event-assets', data / 'roadscore-event-state'
    if not assets.exists() and not state.exists():
        return []  # Existing installations retain their original layout.
    mapping = {name: state / name for name in ('generated', 'results', 'assets', 'runtime.json')}
    mapping.update({f'experiments/ace_chestnut_20260916/{name}': assets / 'ace' / name
                    for name in ('weights', 'vae_weights', 'profiles')})
    missing = []
    for relative, target in mapping.items():
        valid = target.is_file() if relative == 'runtime.json' else target.is_dir()
        if not valid:
            raise RuntimeError(f'Persistent RoadScore asset missing: {target}; restore it before launch')
        link = root / relative
        if link.is_symlink():
            if link.resolve() != target.resolve():
                raise RuntimeError(f'Refusing to replace another link: {link}')
        elif link.exists():
            raise RuntimeError(f'Refusing to overwrite checkout data: {link}')
        else:
            missing.append((link, target))
    # Validate the entire map before changing anything. Never delete or move data.
    for link, target in missing:
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(target, target_is_directory=target.is_dir())
    return [str(link) for link, _ in missing]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path('/data/roadscore'))
    args = parser.parse_args()
    for path in restore_links(args.root):
        print(f'Reconnected persistent RoadScore path: {path}')
