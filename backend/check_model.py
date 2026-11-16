"""Offline full-model loading smoke test using the configured local assets."""
from dermfm.service import InferenceService, Settings
if __name__ == '__main__':
    service=InferenceService(Settings.from_env())
    print('Loaded:',service.version,'members:',len(service.states),'device:',service.settings.device)
