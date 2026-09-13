import unittest
from openline_reports.swarm.identity_binding import make_identity_binding_proposal
class T(unittest.TestCase):
    def test_no_authority(self):
        p=make_identity_binding_proposal(proposal_id="p",target_entity="t",candidate_entity="c",evidence=[{"attribute":"name","target_value":"A","candidate_value":"A","source_id":"s"}])
        self.assertEqual(p["authority"],"NONE"); self.assertIsNone(p["requested_disposition"])
    def test_unknown_field_fails(self):
        with self.assertRaises(ValueError): make_identity_binding_proposal(proposal_id="p",target_entity="t",candidate_entity="c",evidence=[{"attribute":"name","target_value":"A","candidate_value":"A","source_id":"s","decision":"COMMIT"}])
if __name__=="__main__": unittest.main()
