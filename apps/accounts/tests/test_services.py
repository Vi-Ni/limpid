from django.test import TestCase, override_settings

from apps.accounts.services import calculate_risk_score, get_risk_profile_label


class CalculateRiskScoreTest(TestCase):
    def test_empty_responses(self):
        assert calculate_risk_score({}) == 1

    def test_all_minimum_answers(self):
        responses = {
            "investment_knowledge": 1,
            "time_horizon": 1,
            "risk_comfort": 1,
            "loss_reaction": 1,
            "income_stability": 1,
            "return_expectation": 1,
        }
        assert calculate_risk_score(responses) == 1

    def test_all_maximum_answers(self):
        responses = {
            "investment_knowledge": 4,
            "time_horizon": 4,
            "risk_comfort": 4,
            "loss_reaction": 4,
            "income_stability": 4,
            "return_expectation": 4,
        }
        assert calculate_risk_score(responses) == 10

    def test_moderate_answers(self):
        responses = {
            "investment_knowledge": 2,
            "time_horizon": 3,
            "risk_comfort": 2,
            "loss_reaction": 3,
            "income_stability": 2,
            "return_expectation": 3,
        }
        score = calculate_risk_score(responses)
        assert 4 <= score <= 7

    def test_score_bounds(self):
        for i in range(1, 5):
            responses = {"q1": i, "q2": i}
            score = calculate_risk_score(responses)
            assert 1 <= score <= 10


@override_settings(LANGUAGE_CODE="en")
class GetRiskProfileLabelTest(TestCase):
    def test_conservative(self):
        for score in [1, 2, 3]:
            assert str(get_risk_profile_label(score)) == "Conservative"

    def test_moderate(self):
        for score in [4, 5, 6]:
            assert str(get_risk_profile_label(score)) == "Moderate"

    def test_growth(self):
        for score in [7, 8, 9, 10]:
            assert str(get_risk_profile_label(score)) == "Growth"
