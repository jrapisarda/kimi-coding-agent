"""Proxy tests to execute the Chopan microservice suite."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

# Importing the real tests ensures pytest collects them under the repository root configuration.
from codex_chopan_app.tests.api.test_gateway import *  # noqa: F401,F403
from codex_chopan_app.tests.content.test_content_service import *  # noqa: F401,F403
from codex_chopan_app.tests.email.test_email_service import *  # noqa: F401,F403
from codex_chopan_app.tests.social.test_social_service import *  # noqa: F401,F403
from codex_chopan_app.tests.prospect.test_prospect_service import *  # noqa: F401,F403
from codex_chopan_app.tests.worker.test_tasks import *  # noqa: F401,F403
