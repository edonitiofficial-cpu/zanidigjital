import json
from pathlib import Path
import tempfile
import unittest
from archive_output import create_archive


class ArchiveTests(unittest.TestCase):
    def test_catalog_and_immutable_pages_reconstruct_public_metadata(self):
        records = [dict(slug=f'news-{i}', titulli=f'Lajmi {i}', imazhi='https://example.com/photo.jpg',
                        kategoria='Lajme', komunat=['Pejë'], permbajtja='Private full text') for i in range(410)]
        records.append(dict(slug='duplicate',titulli='Repeated',duplicate_of='news-1'))
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(create_archive(records,folder),3)
            catalog=json.loads((Path(folder)/'news-catalog.json').read_text(encoding='utf-8'))
            self.assertEqual(len(catalog['items']),410)
            self.assertNotIn('photo.jpg',json.dumps(catalog))
            self.assertNotIn('Private full text',json.dumps(catalog))
            for row in catalog['items']:
                page=json.loads((Path(folder)/catalog['pages'][row[-1]].lstrip('/')).read_text(encoding='utf-8'))
                self.assertTrue(any(n['slug']==row[0] and n['titulli']==row[1] for n in page))
            old=list(catalog['pages'])
            records[0]['titulli']='Updated'
            create_archive(records,folder)
            new=json.loads((Path(folder)/'news-catalog.json').read_text(encoding='utf-8'))
            self.assertNotEqual(old[0],new['pages'][0])
            self.assertEqual(old[1:],new['pages'][1:])
            self.assertTrue((Path(folder)/old[0].lstrip('/')).exists())
