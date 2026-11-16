import io
import unittest
from request_pages_build import request_build
from urllib.error import HTTPError


class PagesTests(unittest.TestCase):
    def test_build_is_requested_explicitly_with_workflow_token(self):
        seen=[]
        def open_request(req,timeout):
            seen.append(req)
            return io.BytesIO(b'{"status":"queued"}')
        self.assertEqual(request_build('owner/repo','private-test-token',open_request),'queued')
        self.assertEqual(seen[0].get_method(),'POST')
        self.assertEqual(seen[0].full_url,'https://api.github.com/repos/owner/repo/pages/builds')

    def test_failure_message_does_not_echo_credentials(self):
        def fail(req,timeout):raise HTTPError(req.full_url,403,'private-test-token',{},None)
        with self.assertRaises(RuntimeError) as error:request_build('owner/repo','private-test-token',fail)
        self.assertNotIn('private-test-token',str(error.exception))
        self.assertIn('403',str(error.exception))
