import json
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from outreach.firefox import search_firefox


class FirefoxHandoffTests(unittest.TestCase):
    def run_handoff(self, exercise):
        with ThreadPoolExecutor(max_workers=1) as pool:
            requests = []

            def open_tab(url):
                requests.append(pool.submit(exercise, url))

            try:
                with patch("outreach.firefox.open_firefox", open_tab):
                    return search_firefox([{"keywords": "Microsoft", "direct": True}], timeout=3)
            finally:
                for request in requests:
                    request.result(timeout=5)

    def get(self, url):
        with urlopen(url, timeout=2) as response:
            return json.load(response)

    def post(self, url, payload, content_type="application/json"):
        request = Request(url + "/result", data=json.dumps(payload).encode(), headers={"Content-Type": content_type})
        with urlopen(request, timeout=2) as response:
            return json.load(response)

    def test_one_use_handoff_rejects_untrusted_requests_and_returns_profiles(self):
        profiles = [{"name": "Test Person", "url": "https://www.linkedin.com/in/test-person", "snippet": "USF · Microsoft intern", "direct": True}]

        def exercise(url):
            for request, status in [
                (url + "wrong/job", 404),
                (Request(url + "/job", headers={"Host": "attacker.example"}), 403),
            ]:
                with self.assertRaises(HTTPError) as error:
                    self.get(request)
                self.assertEqual(error.exception.code, status)
                error.exception.close()
            self.assertEqual(self.get(url + "/job")["queries"][0]["keywords"], "Microsoft")
            with self.assertRaises(HTTPError) as error:
                self.get(url + "/job")
            self.assertEqual(error.exception.code, 409)
            error.exception.close()
            for payload, content_type in [
                ({"results": profiles}, "text/plain"),
                ({"results": [{**profiles[0], "url": "https://attacker.example/in/test-person"}]}, "application/json"),
            ]:
                with self.assertRaises(HTTPError) as error:
                    self.post(url, payload, content_type)
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
            self.post(url, {"results": profiles})

        self.assertEqual(self.run_handoff(exercise), profiles)

    def test_explicit_empty_result_is_empty(self):
        def exercise(url):
            self.get(url + "/job")
            self.post(url, {"results": []})
        self.assertEqual(self.run_handoff(exercise), [])

    def test_browser_error_is_not_empty(self):
        def exercise(url):
            self.get(url + "/job")
            self.post(url, {"error": "LinkedIn requires sign-in"})
        with self.assertRaisesRegex(RuntimeError, "requires sign-in"):
            self.run_handoff(exercise)

    def test_missing_extension_does_not_report_empty(self):
        with patch("outreach.firefox.open_firefox"):
            with self.assertRaisesRegex(RuntimeError, "did not return"):
                search_firefox([], timeout=0)


if __name__ == "__main__":
    unittest.main()
