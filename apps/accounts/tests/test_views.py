from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.accounts.models import RiskQuizResponse, UserProfile

User = get_user_model()


class HomeViewTest(TestCase):
    def test_home_page_returns_200(self):
        response = self.client.get("/")
        assert response.status_code == 200

    def test_home_page_uses_correct_template(self):
        response = self.client.get("/")
        self.assertTemplateUsed(response, "pages/home.html")


class ProfileViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    def test_redirect_when_not_authenticated(self):
        response = self.client.get("/accounts/profile/")
        assert response.status_code == 302

    def test_profile_page_returns_200(self):
        self.client.login(email="test@example.com", password="testpass123")
        response = self.client.get("/accounts/profile/")
        assert response.status_code == 200
        self.assertTemplateUsed(response, "accounts/profile.html")

    def test_profile_auto_creates_user_profile(self):
        self.client.login(email="test@example.com", password="testpass123")
        self.client.get("/accounts/profile/")
        assert UserProfile.objects.filter(user=self.user).exists()

    def test_profile_update(self):
        self.client.login(email="test@example.com", password="testpass123")
        response = self.client.post("/accounts/profile/", {"province": "QC", "preferred_language": "fr"})
        assert response.status_code == 200
        profile = UserProfile.objects.get(user=self.user)
        assert profile.province == "QC"


class OnboardingViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.client.login(email="test@example.com", password="testpass123")

    def test_onboarding_returns_200(self):
        response = self.client.get("/accounts/onboarding/")
        assert response.status_code == 200
        self.assertTemplateUsed(response, "accounts/onboarding.html")

    def test_onboarding_redirects_if_completed(self):
        UserProfile.objects.create(user=self.user, onboarding_completed=True)
        response = self.client.get("/accounts/onboarding/")
        assert response.status_code == 302

    def test_onboarding_step1_post(self):
        response = self.client.post("/accounts/onboarding/step/1/", {"province": "ON"})
        assert response.status_code == 200
        profile = UserProfile.objects.get(user=self.user)
        assert profile.province == "ON"

    def test_onboarding_step2_post(self):
        UserProfile.objects.create(user=self.user)
        response = self.client.post("/accounts/onboarding/step/2/", {"preferred_language": "en"})
        assert response.status_code == 200
        profile = UserProfile.objects.get(user=self.user)
        assert profile.preferred_language == "en"

    def test_onboarding_step3_completes(self):
        UserProfile.objects.create(user=self.user)
        response = self.client.get("/accounts/onboarding/step/3/")
        assert response.status_code == 302
        profile = UserProfile.objects.get(user=self.user)
        assert profile.onboarding_completed is True


class RiskQuizViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.client.login(email="test@example.com", password="testpass123")

    def test_quiz_returns_200(self):
        response = self.client.get("/accounts/risk-quiz/")
        assert response.status_code == 200
        self.assertTemplateUsed(response, "accounts/risk_quiz.html")

    def test_quiz_step_post_saves_response(self):
        response = self.client.post("/accounts/risk-quiz/step/1/", {"answer": "3"})
        assert response.status_code == 200
        assert RiskQuizResponse.objects.filter(user=self.user).count() == 1

    def test_quiz_full_flow(self):
        from apps.accounts.services import QUIZ_QUESTIONS

        for i, _q in enumerate(QUIZ_QUESTIONS, start=1):
            response = self.client.post(f"/accounts/risk-quiz/step/{i}/", {"answer": "3"})
            assert response.status_code == 200

        assert RiskQuizResponse.objects.filter(user=self.user).count() == len(QUIZ_QUESTIONS)
        profile = UserProfile.objects.get(user=self.user)
        assert profile.risk_profile_score is not None

    def test_quiz_results_page(self):
        RiskQuizResponse.objects.create(user=self.user, question_key="q1", answer_value=3)
        response = self.client.get("/accounts/risk-quiz/results/")
        assert response.status_code == 200
