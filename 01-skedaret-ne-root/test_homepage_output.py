from pathlib import Path
import tempfile
import unittest
from homepage_output import render_homepage


class HomepageTests(unittest.TestCase):
    def test_unranked_stories_do_not_fill_slots_rejected_by_editorial_selection(self):
        template='<div><!-- featured:start --><!-- featured:end --></div><div><!-- latest:start --><!-- latest:end --></div>'
        records=[dict(slug='selected',titulli='Selected',featured_rank=1),dict(slug='other',titulli='Other')]
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'index.html';path.write_text(template)
            render_homepage(records,path)
            featured=path.read_text().split('<!-- featured:start -->')[1].split('<!-- featured:end -->')[0]
            self.assertIn('/selected/',featured)
            self.assertNotIn('/other/',featured)

    def test_static_links_are_safe_repeatable_and_refreshable(self):
        template = '''<div id="bento-grid"><!-- featured:start --><!-- featured:end --></div>
          <div id="te-fundit-grid"><!-- latest:start --><!-- latest:end --></div>'''
        records = [dict(slug=f'news-{i}',titulli='<img src=x onerror=alert(1)>',kategoria='Lajme',imazhi='javascript:bad') for i in range(24)]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'index.html';path.write_text(template)
            render_homepage(records,path)
            first = path.read_text()
            self.assertEqual(first.count('href="/lajme/'),21)
            self.assertNotIn('<img src=x',first)
            self.assertNotIn('javascript:bad',first)
            render_homepage(records,path)
            self.assertEqual(first,path.read_text())
            records[0]['titulli']='Updated title'
            render_homepage(records,path)
            self.assertIn('Updated title',path.read_text())
