from django.test import TestCase


class HomeViewTest(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        assert response.status_code == 200

    def test_home_page_uses_correct_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "pages/home.html")
