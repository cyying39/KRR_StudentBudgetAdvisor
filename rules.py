from experta import *

class UserData(Fact):
    """User financial data"""
    pass

class BudgetAdvisor(KnowledgeEngine):

    @Rule(UserData(savings_percent=P(lambda x: x < 10)))
    def low_savings(self):
        print("Warning: Your savings are below 10% of your income.")

    @Rule(UserData(debt_percent=P(lambda x: x > 20)))
    def pay_debt(self):
        print("Warning: More than 20% of your income goes to debt repayment.")

    @Rule(UserData(savings_percent=P(lambda x: x > 20)))
    def encourage_investment(self):
        print("Recommendation: Consider investment as part of your savings.")

    @Rule(UserData(expenses_tracking=False))
    def recommend_track_expenses(self):
        print("Recommendation: Track daily expenses to manage your budget better.")

    @Rule(UserData(subscription_percent=P(lambda x: x > 10)))
    def recommend_reduce_subscriptions(self):
        print("Recommendation: Reduce unnecessary subscriptions.")

    @Rule(UserData(emergency_fund=P(lambda x: x < 500)))
    def low_emergency_fund(self):
        print("Recommendation: Build an emergency fund for unexpected expenses.")

    @Rule(UserData(goal_exists=True, savings=P(lambda x: x < 500), goal_amount=1000))
    def low_savings_for_goal(self):
        print("Recommendation: Create a monthly savings plan to reach your goal.")

    @Rule(UserData(wants_percent=P(lambda x: x > 30)))
    def high_wants_spending(self):
        print("Warning: Too much spending on non-essentials. Consider adjusting your budget.")

#testing, hardcoded before connecting to streamlit
if __name__ == "__main__":
    engine = BudgetAdvisor()
    engine.reset()
    engine.declare(UserData(
        savings_percent=5,
        debt_percent=25,
        subscription_percent=15,
        expenses_tracking=False,
        emergency_fund=300,
        goal_exists=True,
        savings=400,
        goal_amount=1000,
        wants_percent=35
    ))
    engine.run()
