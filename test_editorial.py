from datetime import datetime
import unittest
from article_renderer import related_articles
from news_policy import select_featured, rank_article
from news_time import NEWS_TIMEZONE
from news_utils import homepage_metadata

NOW=datetime(2026,11,15,12,tzinfo=NEWS_TIMEZONE)


def story(title,slug,category='Lajme',host='one.example'):
    return dict(titulli=title,slug=slug,kategoria=category,published_at=NOW.isoformat(),
                link_origjinal=f'https://{host}/{slug}',komunat=[])


class EditorialTests(unittest.TestCase):
    def test_homepage_keeps_ranked_story_outside_first_150(self):
        rows=[story(f'Article number {i}',str(i)) for i in range(220)]
        rows[180]['featured_rank']=1
        result=homepage_metadata(rows)
        self.assertEqual(len(result),150)
        self.assertTrue(any(n['slug']=='180' and n['featured_rank']==1 for n in result))
        self.assertEqual(result[0]['slug'],'0')
    def test_public_services_outrank_live_scores_of_equal_age(self):
        score=story('GOOOL 2-1, Barcelona kalon në epërsi','goal','Sport')
        service=story('Ndërprerje uji në Pejë për shkak të punimeve','water')
        rows=[score,service,story('Shkollat hapen të hënën','school',host='two.example'),
              story('Spitali hap shërbimin e ri','hospital',host='three.example'),
              story('Rriten pensionet nga janari','pensions',host='four.example')]
        chosen=select_featured(rows,NOW)
        self.assertEqual(chosen[0]['slug'],'water')
        self.assertLess(rank_article(score,NOW)[0],rank_article(service,NOW)[0])

    def test_repeated_topic_updates_give_way_to_other_subjects(self):
        pensions=[story(f'Qeveria miraton rritjen e pensioneve për {n} për qind',f'p-{n}',host=f'{n}.example') for n in [10,12,14,16]]
        alternatives=[story('Shkollat fillojnë regjistrimin e nxënësve','school','Lajme','school.example'),
                      story('Mjekët nisin vaksinimin sezonal','health','Lajme','health.example'),
                      story('Rruga e re hapet për trafik','road','Lajme','road.example'),
                      story('Finalja evropiane zhvillohet sonte','sport','Sport','sport.example')]
        chosen=select_featured(pensions+alternatives,NOW)
        self.assertEqual(len(chosen),5)
        self.assertEqual(sum(n['slug'].startswith('p-') for n in chosen),1)

    def test_selection_fills_when_all_sources_and_categories_are_identical(self):
        rows=[story(title,str(i)) for i,title in enumerate([
            'Hapet rruga e re në qytet','Shkollat nisin mësimin','Spitali merr pajisje',
            'Rriten pagat në administratë','Publikohet një libër historik'])]
        chosen=select_featured(rows,NOW)
        self.assertEqual(len(chosen),5)
        self.assertEqual([n['featured_rank'] for n in chosen],[1,2,3,4,5])

    def test_related_news_prefers_topic_category_and_place(self):
        article=story('Ndërprerje uji në Pejë për shkak të punimeve','main','Lajme')
        article['komunat']=['Pejë']
        unrelated=story('Barcelona fiton finalen evropiane','football','Sport')
        local=story('Ujësjellësi investon në rrjetin e Pejës','local','Lajme')
        local['komunat']=['Pejë']
        repeated=dict(article,slug='copy')
        related=related_articles(article,[unrelated,repeated,local,dict(local,slug='duplicate',duplicate_of='local')])
        self.assertEqual(related[0]['slug'],'local')
        self.assertNotIn('copy',[n['slug'] for n in related])
        self.assertNotIn('duplicate',[n['slug'] for n in related])
