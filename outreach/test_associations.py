import csv
import tempfile
import unittest
from pathlib import Path

from outreach.associations import connection_candidates


class ConnectionCandidatesTests(unittest.TestCase):
    def test_finds_usf_connection_with_microsoft_profile_experience(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Connections.csv"
            with path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "First Name",
                        "Last Name",
                        "Profile URL",
                        "Position",
                        "Company",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "First Name": "Fagan",
                        "Last Name": "Afandiyev",
                        "Profile URL": "https://www.linkedin.com/in/fagan-afandi",
                        "Position": "Student",
                        "Company": "University of South Florida",
                    }
                )

            def fetch_profile(url: str) -> str:
                return "Fagan Afandiyev completed a penetration-testing internship at Microsoft."

            candidates = connection_candidates(
                path,
                "Microsoft",
                ["University of South Florida"],
                fetch_profile,
            )

        self.assertEqual(candidates[0][0].name, "Fagan Afandiyev")
        self.assertEqual(
            candidates[0][1],
            ["University of South Florida", "LinkedIn profile: Microsoft"],
        )




if __name__ == "__main__":
    unittest.main()
