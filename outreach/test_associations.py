import unittest
from io import StringIO
from unittest.mock import patch

from outreach.associations import main


class AssociationCliTests(unittest.TestCase):
    def test_searches_firefox_without_prompting_for_csv(self) -> None:
        output = StringIO()
        with (
            patch("outreach.associations.applicant_details", return_value=("https://www.linkedin.com/in/applicant/", ["University of South Florida"])),
            patch("outreach.associations.linkedin_candidates", return_value=[]) as candidates,
            patch("builtins.input", side_effect=["Microsoft", ""]),
            patch("sys.stdout", output),
        ):
            main()

        candidates.assert_called_once_with("Microsoft", ["University of South Florida"])
        self.assertIn("No matches returned by LinkedIn people search", output.getvalue())


if __name__ == "__main__":
    unittest.main()
