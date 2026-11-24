"""Check that a configured E38 fold propagates gradients to one image input."""
import argparse
import ctypes
import os
import sys
import time

import torch

def peak_memory_bytes(device):
    if device.startswith('cuda'):
        return torch.cuda.max_memory_allocated()
    if os.name == 'nt':
        class Counters(ctypes.Structure):
            _fields_ = [('cb', ctypes.c_ulong), ('PageFaultCount', ctypes.c_ulong),
                ('PeakWorkingSetSize', ctypes.c_size_t), ('WorkingSetSize', ctypes.c_size_t),
                ('QuotaPeakPagedPoolUsage', ctypes.c_size_t), ('QuotaPagedPoolUsage', ctypes.c_size_t),
                ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t), ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
                ('PagefileUsage', ctypes.c_size_t), ('PeakPagefileUsage', ctypes.c_size_t)]
        counters = Counters(); counters.cb = ctypes.sizeof(counters)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return int(counters.PeakWorkingSetSize)
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return int(peak * (1024 if sys.platform != 'darwin' else 1))
    except (ImportError, AttributeError):
        return -1

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from dermfm.preprocessing import decode_image, prepare_inputs
from dermfm.service import InferenceService, Settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('image', help='Path to a test JPG, PNG or WebP image')
    parser.add_argument('--target', type=int, default=0)
    args = parser.parse_args()
    service = InferenceService(Settings.from_env())
    with open(args.image, 'rb') as stream:
        image = decode_image(stream.read())
    derm, clinical, meta = prepare_inputs(image, 50, 'female', service.loaded.eval_transform,
                                          service.settings.device, 'unknown')
    derm = derm.detach().float().requires_grad_(True)
    started = time.perf_counter()
    if service.settings.device.startswith('cuda'):
        torch.cuda.reset_peak_memory_stats()
    service.loaded.model.eval()
    service.loaded.model.zero_grad(set_to_none=True)
    logit = service.loaded.model(derm, clinical.float(), meta.float())[0, args.target]
    logit.backward()
    gradient = derm.grad
    assert gradient is not None and torch.isfinite(gradient).all() and gradient.abs().sum() > 0
    peak = peak_memory_bytes(service.settings.device)
    print(f'logit={logit.item():.8f}')
    print(f'gradient_norm={gradient.norm().item():.8f}')
    print(f'peak_memory_bytes={peak}')
    print(f'elapsed_seconds={time.perf_counter()-started:.3f}')


if __name__ == '__main__':
    main()
