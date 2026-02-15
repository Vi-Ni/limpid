from django.utils.translation import gettext_lazy as _

QUIZ_QUESTIONS = [
    {
        "key": "investment_knowledge",
        "text": _("How would you describe your investment knowledge?"),
        "choices": [
            (1, _("I'm a complete beginner")),
            (2, _("I know the basics (stocks, bonds, ETFs)")),
            (3, _("I have intermediate knowledge and some experience")),
            (4, _("I'm experienced and understand most financial products")),
        ],
    },
    {
        "key": "time_horizon",
        "text": _("What is your investment time horizon?"),
        "choices": [
            (1, _("Less than 2 years")),
            (2, _("2 to 5 years")),
            (3, _("5 to 10 years")),
            (4, _("More than 10 years")),
        ],
    },
    {
        "key": "risk_comfort",
        "text": _("If your portfolio lost 20% of its value in a month, what would you do?"),
        "choices": [
            (1, _("Sell everything immediately")),
            (2, _("Sell some to reduce risk")),
            (3, _("Do nothing and wait for recovery")),
            (4, _("Buy more at the lower price")),
        ],
    },
    {
        "key": "loss_reaction",
        "text": _("How much of your portfolio could you afford to lose without impacting your lifestyle?"),
        "choices": [
            (1, _("None — I need all of it")),
            (2, _("Up to 10%")),
            (3, _("Up to 25%")),
            (4, _("More than 25%")),
        ],
    },
    {
        "key": "income_stability",
        "text": _("How stable is your current income?"),
        "choices": [
            (1, _("Very unstable or no income")),
            (2, _("Somewhat unstable")),
            (3, _("Stable with some variability")),
            (4, _("Very stable (salaried, tenured, etc.)")),
        ],
    },
    {
        "key": "return_expectation",
        "text": _("Which statement best describes your return expectations?"),
        "choices": [
            (1, _("I want to preserve my capital, even if returns are low")),
            (2, _("I prefer steady, modest returns with low risk")),
            (3, _("I want a balance of growth and stability")),
            (4, _("I want maximum growth, even if it means high volatility")),
        ],
    },
]


def calculate_risk_score(responses):
    """Calculate a risk score from 1-10 based on quiz responses.

    responses: dict of {question_key: answer_value}
    Returns an integer score from 1 to 10.
    """
    if not responses:
        return 1

    total = sum(responses.values())
    num_questions = len(responses)
    max_possible = num_questions * 4
    min_possible = num_questions * 1

    normalized = (total - min_possible) / (max_possible - min_possible)
    score = round(normalized * 9) + 1
    return max(1, min(10, score))


def get_risk_profile_label(score):
    """Return a human-readable risk profile label."""
    if score <= 3:
        return _("Conservative")
    if score <= 6:
        return _("Moderate")
    return _("Growth")


def get_risk_profile_description(score):
    """Return educational description for the risk profile."""
    if score <= 3:
        return _(
            "You prefer stability and capital preservation. A conservative "
            "portfolio typically holds more bonds and GICs, with limited "
            "exposure to stocks. Returns may be lower, but so is the risk "
            "of losing money."
        )
    if score <= 6:
        return _(
            "You seek a balance between growth and safety. A moderate "
            "portfolio typically includes a mix of stocks and bonds, "
            "offering reasonable growth potential while managing downside "
            "risk."
        )
    return _(
        "You are comfortable with higher volatility in exchange for "
        "potentially higher returns. A growth portfolio is typically "
        "stock-heavy, which means larger swings but historically better "
        "long-term performance."
    )
