import pytest
import hashlib
import mysql.connector
from unittest.mock import Mock, patch, MagicMock
from experta import *

# # Run all tests without coverage
# pytest test_budget_advisor.py -v
#
# # Run specific test classes
# pytest test_budget_advisor.py::TestBudgetAdvisor -v
# pytest test_budget_advisor.py::TestDatabaseFunctions -v
# pytest test_budget_advisor.py::TestUtilityFunctions -v
# pytest test_budget_advisor.py::TestIntegration -v

# Define all the functions and classes needed for testing
def get_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="budget_app"
    )


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def check_credentials(username, password):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, password FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if result:
        user_id, stored_hash = result
        if stored_hash == hash_password(password):
            return user_id
    return None


def create_user(username, password):
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)",
                       (username, hash_password(password)))
        conn.commit()
        return True
    except mysql.connector.errors.IntegrityError:
        return False
    finally:
        cursor.close()
        conn.close()


def insert_advice_to_db(user_id, data_dict, advice_text):
    conn = get_connection()
    cursor = conn.cursor()

    query = """
        INSERT INTO advice_log (
            user_id, savings_percent, debt_percent, subscription_percent, expenses_tracking,
            emergency_fund, wants_percent, goal_exists, savings, goal_amount, advice_text
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    values = (
        user_id,
        data_dict['savings_percent'],
        data_dict['debt_percent'],
        data_dict['subscription_percent'],
        data_dict['expenses_tracking'],
        data_dict['emergency_fund'],
        data_dict['wants_percent'],
        data_dict['goal_exists'],
        data_dict['savings'],
        data_dict['goal_amount'],
        advice_text
    )

    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()


def get_user_advice_history(user_id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT created_at, savings_percent, debt_percent, wants_percent, advice_text
        FROM advice_log
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (user_id,))

    results = cursor.fetchall()
    cursor.close()
    conn.close()
    return results


class UserData(Fact):
    pass


class BudgetAdvisor(KnowledgeEngine):
    def __init__(self):
        super().__init__()
        self.advice_list = []

    def _add_advice(self, msg):
        self.advice_list.append(msg)

    @Rule(UserData(savings_percent=P(lambda x: x < 10)))
    def low_savings(self):
        self._add_advice("⚠️ Your savings are below 10% of your income.")

    @Rule(UserData(debt_percent=P(lambda x: x > 20)))
    def pay_debt(self):
        self._add_advice("⚠️ More than 20% of your income goes to debt repayment.")

    @Rule(UserData(savings_percent=P(lambda x: x > 20)))
    def encourage_investment(self):
        self._add_advice("✅ Consider investment as part of your savings.")

    @Rule(UserData(expenses_tracking=False))
    def recommend_track_expenses(self):
        self._add_advice("📌 Track daily expenses to manage your budget better.")

    @Rule(UserData(subscription_percent=P(lambda x: x > 10)))
    def recommend_reduce_subscriptions(self):
        self._add_advice("📌 Reduce unnecessary subscriptions.")

    @Rule(UserData(emergency_fund=P(lambda x: x < 500)))
    def low_emergency_fund(self):
        self._add_advice("📌 Build an emergency fund for unexpected expenses.")

    @Rule(UserData(goal_exists=True, savings=MATCH.s, goal_amount=MATCH.g))
    def low_savings_for_goal(self, s, g):
        if s < g:
            self._add_advice("📌 Create a monthly savings plan to reach your goal.")

    @Rule(UserData(wants_percent=P(lambda x: x > 30)))
    def high_wants_spending(self):
        self._add_advice("⚠️ Too much spending on non-essentials.")


# Mock functions for database operations
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


class TestBudgetAdvisor:
    """Test cases for the BudgetAdvisor expert system"""

    def setup_method(self):
        """Setup method to create a fresh engine for each test"""
        self.engine = BudgetAdvisor()

    def test_low_savings_rule(self):
        """Test advice for low savings percentage"""
        self.engine.reset()
        self.engine.declare(UserData(savings_percent=5))
        self.engine.run()

        assert "⚠️ Your savings are below 10% of your income." in self.engine.advice_list

    def test_high_debt_rule(self):
        """Test advice for high debt percentage"""
        self.engine.reset()
        self.engine.declare(UserData(debt_percent=25))
        self.engine.run()

        assert "⚠️ More than 20% of your income goes to debt repayment." in self.engine.advice_list

    def test_encourage_investment_rule(self):
        """Test advice for high savings percentage"""
        self.engine.reset()
        self.engine.declare(UserData(savings_percent=25))
        self.engine.run()

        assert "✅ Consider investment as part of your savings." in self.engine.advice_list

    def test_track_expenses_rule(self):
        """Test advice for not tracking expenses"""
        self.engine.reset()
        self.engine.declare(UserData(expenses_tracking=False))
        self.engine.run()

        assert "📌 Track daily expenses to manage your budget better." in self.engine.advice_list

    def test_reduce_subscriptions_rule(self):
        """Test advice for high subscription percentage"""
        self.engine.reset()
        self.engine.declare(UserData(subscription_percent=15))
        self.engine.run()

        assert "📌 Reduce unnecessary subscriptions." in self.engine.advice_list

    def test_low_emergency_fund_rule(self):
        """Test advice for low emergency fund"""
        self.engine.reset()
        self.engine.declare(UserData(emergency_fund=300))
        self.engine.run()

        assert "📌 Build an emergency fund for unexpected expenses." in self.engine.advice_list

    def test_goal_savings_rule(self):
        """Test advice for insufficient savings towards goal"""
        self.engine.reset()
        self.engine.declare(UserData(
            goal_exists=True,
            savings=1000,
            goal_amount=5000
        ))
        self.engine.run()

        assert "📌 Create a monthly savings plan to reach your goal." in self.engine.advice_list

    def test_high_wants_spending_rule(self):
        """Test advice for high wants spending"""
        self.engine.reset()
        self.engine.declare(UserData(wants_percent=40))
        self.engine.run()

        assert "⚠️ Too much spending on non-essentials." in self.engine.advice_list

    def test_multiple_rules_triggered(self):
        """Test when multiple rules are triggered"""
        self.engine.reset()
        self.engine.declare(UserData(
            savings_percent=5,  # Low savings
            debt_percent=25,  # High debt
            wants_percent=35,  # High wants
            expenses_tracking=False  # Not tracking
        ))
        self.engine.run()

        # Should have 4 pieces of advice
        assert len(self.engine.advice_list) == 4
        assert "⚠️ Your savings are below 10% of your income." in self.engine.advice_list
        assert "⚠️ More than 20% of your income goes to debt repayment." in self.engine.advice_list
        assert "⚠️ Too much spending on non-essentials." in self.engine.advice_list
        assert "📌 Track daily expenses to manage your budget better." in self.engine.advice_list

    def test_no_advice_needed(self):
        """Test when financial situation is healthy"""
        self.engine.reset()
        self.engine.declare(UserData(
            savings_percent=15,
            debt_percent=10,
            wants_percent=20,
            expenses_tracking=True,
            emergency_fund=1000,
            subscription_percent=5,
            goal_exists=False
        ))
        self.engine.run()

        # Should have no advice (healthy finances)
        assert len(self.engine.advice_list) == 0


class TestUtilityFunctions:
    """Test cases for utility functions"""

    def test_hash_password(self):
        """Test password hashing function"""
        password = "test123"
        hashed = hash_password(password)

        # Should return a hex string
        assert isinstance(hashed, str)
        assert len(hashed) == 64  # SHA256 produces 64-character hex string

        # Same password should produce same hash
        assert hash_password(password) == hashed

        # Different passwords should produce different hashes
        assert hash_password("different") != hashed


class TestDatabaseFunctions:
    """Test cases for database functions with mocking"""

    @patch('test_budget_advisor.get_connection')
    def test_get_connection(self, mock_get_connection):
        """Test database connection"""

        mock_conn = Mock()
        mock_get_connection.return_value = mock_conn

        conn = get_connection()

        mock_get_connection.assert_called_once()
        assert conn == mock_conn

    @patch('test_budget_advisor.get_connection')
    def test_check_credentials_valid(self, mock_get_connection):
        """Test checking valid credentials"""

        # Mock database connection and cursor
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock successful credential check
        test_password = "test123"
        hashed_password = hash_password(test_password)
        mock_cursor.fetchone.return_value = (1, hashed_password)

        result = check_credentials("testuser", test_password)

        assert result == 1
        mock_cursor.execute.assert_called_once_with(
            "SELECT user_id, password FROM users WHERE username = %s",
            ("testuser",)
        )

    @patch('test_budget_advisor.get_connection')
    def test_check_credentials_invalid(self, mock_get_connection):
        """Test checking invalid credentials"""

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock failed credential check
        mock_cursor.fetchone.return_value = None

        result = check_credentials("nonexistent", "wrongpass")

        assert result is None

    @patch('test_budget_advisor.get_connection')
    def test_create_user_success(self, mock_get_connection):
        """Test successful user creation"""

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        result = create_user("newuser", "password123")

        assert result is True
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('test_budget_advisor.get_connection')
    def test_create_user_duplicate(self, mock_get_connection):
        """Test user creation with duplicate username"""

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock IntegrityError for duplicate username
        mock_cursor.execute.side_effect = mysql.connector.errors.IntegrityError("Duplicate entry")

        result = create_user("existinguser", "password123")

        assert result is False

    @patch('test_budget_advisor.get_connection')
    def test_insert_advice_to_db(self, mock_get_connection):
        """Test inserting advice to database"""

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        test_data = {
            'savings_percent': 15,
            'debt_percent': 10,
            'subscription_percent': 5,
            'expenses_tracking': True,
            'emergency_fund': 1000,
            'wants_percent': 25,
            'goal_exists': True,
            'savings': 500,
            'goal_amount': 2000
        }

        insert_advice_to_db(1, test_data, "Test advice")

        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()

    @patch('test_budget_advisor.get_connection')
    def test_get_user_advice_history(self, mock_get_connection):
        """Test retrieving user advice history"""

        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_connection.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor

        # Mock return data
        mock_cursor.fetchall.return_value = [
            {
                'created_at': '2024-01-01 10:00:00',
                'savings_percent': 15,
                'debt_percent': 10,
                'wants_percent': 25,
                'advice_text': 'Test advice'
            }
        ]

        result = get_user_advice_history(1)

        assert len(result) == 1
        assert result[0]['advice_text'] == 'Test advice'
        mock_cursor.execute.assert_called_once_with(
            """
        SELECT created_at, savings_percent, debt_percent, wants_percent, advice_text
        FROM advice_log
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 10
    """, (1,)
        )


class TestIntegration:
    """Integration tests combining multiple components"""

    def test_complete_advice_flow(self):
        """Test complete flow from user data to advice generation"""
        engine = BudgetAdvisor()
        engine.reset()

        # Simulate problematic financial situation
        user_data = UserData(
            savings_percent=5,  # Too low
            debt_percent=25,  # Too high
            subscription_percent=15,  # Too high
            expenses_tracking=False,  # Should track
            emergency_fund=200,  # Too low
            wants_percent=40,  # Too high
            goal_exists=True,
            savings=500,
            goal_amount=2000  # Need savings plan
        )

        engine.declare(user_data)
        engine.run()

        # Should generate multiple pieces of advice
        expected_advice_count = 7  # All rules should trigger
        assert len(engine.advice_list) == expected_advice_count

        # Check that all expected advice is present
        advice_text = " ".join(engine.advice_list)
        assert "savings are below 10%" in advice_text
        assert "debt repayment" in advice_text
        assert "subscriptions" in advice_text
        assert "Track daily expenses" in advice_text
        assert "emergency fund" in advice_text
        assert "spending on non-essentials" in advice_text
        assert "savings plan to reach your goal" in advice_text


# Pytest fixtures for common test data
@pytest.fixture
def sample_user_data():
    """Fixture providing sample user data for tests"""
    return {
        'savings_percent': 15,
        'debt_percent': 10,
        'subscription_percent': 5,
        'expenses_tracking': True,
        'emergency_fund': 1000,
        'wants_percent': 25,
        'goal_exists': True,
        'savings': 500,
        'goal_amount': 2000
    }


@pytest.fixture
def problematic_user_data():
    """Fixture providing problematic financial data for tests"""
    return {
        'savings_percent': 3,
        'debt_percent': 30,
        'subscription_percent': 20,
        'expenses_tracking': False,
        'emergency_fund': 100,
        'wants_percent': 50,
        'goal_exists': True,
        'savings': 100,
        'goal_amount': 5000
    }


if __name__ == "__main__":
    # Run tests with: python -m pytest test_budget_advisor.py -v
    pytest.main([__file__, "-v"])