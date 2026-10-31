"""CPU-only environment verification; no physics or changes to external sources."""
import argparse
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import sys
import tempfile


def configure_cache(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    temporary = root/'temporary'
    temporary.mkdir(exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(temporary)
    tempfile.tempdir = str(temporary)
    os.environ['MPLCONFIGDIR'] = str(root/'matplotlib')
    os.environ['XDG_CACHE_HOME'] = str(root)
    os.environ['WANDB_MODE'] = 'disabled'
    import warp as wp
    if not hasattr(wp.config, 'kernel_cache_dir'):
        raise RuntimeError('Unverified Warp cache configuration API')
    wp.config.kernel_cache_dir = str(root/'warp')
    return wp


def verify(cache):
    wp = configure_cache(cache)
    import torch
    import torchvision
    import mujoco
    import mujoco_warp
    del mujoco_warp
    expected = {'torch': '2.9.0+cpu', 'torchvision': '0.24.0+cpu', 'mjlab': '1.2.0',
                'mujoco': '3.5.0', 'mujoco-warp': '3.5.0', 'warp-lang': '1.12.0',
                'rsl-rl-lib': '5.0.1', 'scipy': '1.18.1'}
    versions = {name: metadata.version(name) for name in expected}
    installed = {dist.metadata['Name']: dist.version for dist in metadata.distributions()}
    forbidden = [name for name in installed if name.lower().startswith(('nvidia-', 'nvidia_', 'cuda', 'cupy', 'triton'))]
    checks = dict(python_312=sys.version_info[:2] == (3, 12), windows_x64=platform.system() == 'Windows' and sys.maxsize > 2**32,
        versions_exact=versions == expected, torch_cpu=torch.version.cuda is None,
        torchvision_cpu=torchvision.__version__.endswith('+cpu'), no_gpu_packages=not forbidden)
    wp.init()
    checks['warp_cpu_available'] = bool(wp.get_device('cpu').is_cpu)
    return dict(checks=checks, versions=versions, forbidden_packages=forbidden,
                python=sys.version, installed=installed, physics_executed=False)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    value = verify(a.cache)
    with a.output.open('x', encoding='utf-8') as f:
        json.dump(value, f, indent=2)
    print(json.dumps({k: v for k, v in value.items() if k != 'installed'}, indent=2))
    return 0 if all(value['checks'].values()) else 2


if __name__ == '__main__':
    raise SystemExit(main())
