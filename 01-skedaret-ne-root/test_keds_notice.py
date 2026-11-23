import unittest
from keds_notice import parse_outages


class OutageTests(unittest.TestCase):
    def test_explicit_times_and_locations_stay_paired(self):
        text='Nga TS Peja II do të ndërpritet:\nnga ora 10:00 deri në orën 11:00 Vendet: Tabije, Qendra Arsyeja: Testimi i mbrojtjes\nNga TS Peja II do të ndërpritet nga ora 12:00 deri 13:00 Vendet: Spitali Arsyeja: Mirëmbajtje'
        events=parse_outages(text)
        self.assertEqual(len(events),2)
        self.assertEqual(events[0],dict(start='10:00',end='11:00',locations='Tabije, Qendra',reason='Testimi i mbrojtjes'))
        self.assertEqual(events[1]['locations'],'Spitali')

    def test_alternate_time_wording_and_unknown_notice(self):
        event=parse_outages('prej ores 9:00 deri në ora 16:00\nVendet: Fshati A\nArsyeja: Punime')[0]
        self.assertEqual(event['start'],'09:00')
        self.assertEqual(event['end'],'16:00')
        self.assertEqual(parse_outages('Punime në rrjet, ora nuk është përcaktuar'),[])
        self.assertEqual(parse_outages('nga ora 28:00 deri 30:00'),[])
