import unittest

from omni_scraper.reduce.html_to_markdown import reduce_html


class ReduceTests(unittest.TestCase):
    def test_reduce_html_collects_contact_signals_and_links(self):
        html = """
        <html><head><title>Acme Inc</title><meta name="description" content="Widgets and services"></head>
        <body>
          <nav><a href="/blog">Blog</a></nav>
          <main>
            <h1>Contact Acme</h1>
            <p>Email info@example.com or call (555) 123-4567.</p>
            <a href="/contact">Contact Us</a>
            <a href="/about">About</a>
          </main>
        </body></html>
        """
        page = reduce_html(html, source_url="https://example.com", final_url="https://example.com")

        self.assertIn("# Acme Inc", page.markdown)
        self.assertIn("info@example.com", page.signals["emails"])
        self.assertTrue(page.signals["phones"])
        self.assertTrue(page.link_clusters["contact_likely"])
        self.assertTrue(page.link_clusters["company_likely"])


if __name__ == "__main__":
    unittest.main()
