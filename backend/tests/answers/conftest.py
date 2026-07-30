"""Shared fixtures for the answers tests.

`session_setup` seeds a form with two required fields and one optional
single_choice — exactly the shape the skip tests need. It lives here rather
than being imported test-to-test, which made the fixture name shadow every
test's own parameter.
"""

from tests.answers.test_answers import clean_db, session_setup  # noqa: F401
