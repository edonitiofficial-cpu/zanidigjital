from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import tempfile
import unittest
from municipalities import detect_municipalities, MUNICIPALITIES
from news_policy import find_duplicate, group_archive, merge_source, same_event, select_featured
from news_time import NEWS_TIMEZONE
from robot_report import RunReport

NOW = datetime(2026,11,10,13,0,tzinfo=NEWS_TIMEZONE)


def article(title, slug, hours=0, category='Lajme', host='one.example'):
    return {'titulli':title,'slug':slug,'published_at':(NOW-timedelta(hours=hours)).isoformat(),
            'koha':(NOW-timedelta(hours=hours)).strftime('%d/%m/%Y %H:%M'),
            'link_origjinal':f'https://{host}/{slug}', 'kategoria':category}


class AutomationTests(unittest.TestCase):
    def test_municipalities_are_grounded(self):
        self.assertEqual(len(MUNICIPALITIES),38)
        self.assertEqual(detect_municipalities('Ndërprerje uji në Pejë'), ['Pejë'])
        self.assertEqual(detect_municipalities('Takim në Fushë Kosovë'), ['Fushë Kosovë'])
        self.assertEqual(detect_municipalities('Nga viti 2026 rriten pensionet'), [])
        self.assertEqual(detect_municipalities('Vitia flet për shëndetësinë'), [])
        self.assertEqual(detect_municipalities('Shkollë e re në Viti'), ['Viti'])
        self.assertEqual(detect_municipalities('Investime në Mitrovicën e Veriut'), ['Mitrovicë e Veriut'])
        self.assertEqual(detect_municipalities('Tubim në Mitrovicë'), [])
        self.assertEqual(detect_municipalities('Reforma kombëtare', 'Tekst pa vend.\nHyrje pa vend.\nPërmendet Prizreni në fund.'), [])

    def test_same_event_merges_but_different_incidents_do_not(self):
        first = article('Aksident në Pejë, dy persona të lënduar', 'a')
        second = article('Dy persona të lënduar në aksident në Pejë', 'b', host='two.example')
        self.assertTrue(same_event(first,second))
        self.assertFalse(same_event(first,article('Aksident në Gjilan, dy persona të lënduar','c')))
        self.assertFalse(same_event(article('Në Pejë lëndohen 2 persona në aksident','a'),article('Në Pejë lëndohen 4 persona në aksident','b')))
        self.assertFalse(same_event(article('Albin Kurti kërkon ndryshimin e ligjit për paga','a'),article('Lumir Abdixhiku kërkon ndryshimin e ligjit për paga','b')))
        self.assertFalse(same_event(article('Miratohet ligji për rritjen e pagave','a'),article('Nuk miratohet ligji për rritjen e pagave','b')))
        match, reason = find_duplicate(second,[first],NOW)
        self.assertIs(match,first); self.assertEqual(reason,'same_event')
        self.assertTrue(merge_source(first,second)); self.assertFalse(merge_source(first,second))
        self.assertEqual(len(first['burime']),2)
        payroll_a=article('Elshani: Pagesat u kryen për operatorët, rifillon puna në shkolla','pay-a')
        payroll_b=article('Ekzekutohen pagat e teknikëve, Elshani kërkon përgjegjësi','pay-b')
        payroll_a['permbajtja']='Drejtori i arsimit në Komunën e Prishtinës, Arianit Elshani, njoftoi se pagesat për operatorët ekonomikë dhe punëtorët teknikë të shkollave janë kryer gjatë ditës së djeshme.'
        payroll_b['permbajtja']='Drejtori i arsimit në Prishtinë, Arianit Elshani, njoftoi se pagesat për operatorët ekonomikë dhe punëtorët teknikë të shkollave janë kryer gjatë ditës së djeshme.'
        self.assertTrue(same_event(payroll_a,payroll_b))
        interview_a=article('Haliti flet për periudhën kur ishte lojtar i Prishtinës','haliti-a',category='Sport')
        interview_b=article('Haliti rrëfen për periudhën kur u transferua në Shqipëri','haliti-b',category='Sport')
        interview_a['permbajtja']=interview_b['permbajtja']='Ish futbollisti Ahmet Haliti ishte i ftuar në emisionin sportiv të javës për të diskutuar karrierën e tij dhe momentet e veçanta të futbollit vendor.'
        self.assertFalse(same_event(interview_a,interview_b))
        repeated = article(first['titulli'],'tomorrow',hours=-25)
        self.assertEqual(find_duplicate(repeated,[first],NOW),(None,None))

    def test_archive_grouping_keeps_original_urls(self):
        rows = [article('Aksident në Pejë, dy persona të lënduar','a'),article('Dy persona të lënduar në aksident në Pejë','b',hours=1,host='two.example')]
        self.assertEqual(group_archive(rows),1)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[1]['duplicate_of'],'a')
        self.assertEqual(rows[0]['source_count'],2)
        self.assertEqual(group_archive(rows),0)

    def test_featured_selection_balances_sources_and_recency(self):
        rows = [article('Takimi i fundit i qeverisë','a'),article('Ndërprerje uji në Pejë','b',category='Ekonomi'),
                article('Fitore në finalen evropiane','c',category='Sport',host='two.example'),
                article('Telefon me bateri të re','d',category='Teknologji',host='two.example'),
                article('Hapet shkolla në Prizren','e',host='three.example'),
                article('Lajm i vjetër për pensionet','old',hours=70)]
        selected = select_featured(rows,NOW)
        self.assertEqual(len(selected),5)
        self.assertNotIn('old',[n['slug'] for n in selected])
        self.assertEqual([n['featured_rank'] for n in selected],[1,2,3,4,5])
        self.assertTrue(all(n['selection_reasons'] for n in selected))
        self.assertEqual(len(select_featured(rows[:2],NOW)),2)

    def test_report_preserves_history_without_exception_details(self):
        original=os.getcwd()
        with tempfile.TemporaryDirectory() as folder:
            try:
                os.chdir(folder)
                report=RunReport();report.event('Test','https://example.com','rejected','classification_failed');report.finish('error',error=RuntimeError('SECRET_TOKEN'))
                text=Path('bot-status.json').read_text(encoding='utf-8')
                self.assertNotIn('SECRET_TOKEN',text)
                self.assertEqual(json.loads(text)['counts']['rejected'],1)
                RunReport().finish('ok')
                self.assertEqual(len(json.loads(Path('bot-status.json').read_text())['history']),2)
            finally:os.chdir(original)
