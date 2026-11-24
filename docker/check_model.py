"""Offline verification of the packaged DermFM model."""
import os
from dermfm.e55_service import E55Service

service = E55Service(os.environ.get('E55_BUNDLE_PATH', '/opt/models/dermfm'))
print('DermFM model loaded:', service.version)
