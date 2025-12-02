"""Notification Service - Email notifications and alerts"""
from flask import current_app
from flask_mail import Message
from src.extensions import mail
from src.models.user import User

class NotificationService:
    def __init__(self):
        pass

    def send_email(self, to, subject, html_body):
        """Send email notification"""
        try:
            msg = Message(subject=subject, recipients=[to], html=html_body)
            mail.send(msg)
            return True, 'Email sent successfully'
        except Exception as e:
            current_app.logger.error(f"Email error: {str(e)}")
            return False, f'Error: {str(e)}'

    def send_budget_alert(self, user_id, budget):
        """Send budget overspend alert"""
        user = User.query.get(user_id)
        if not user:
            return False, 'User not found'

        subject = f"Budget Alert: {budget.name}"
        html_body = f"""
        <h2>Budget Alert</h2>
        <p>Your budget for {budget.name} has exceeded its limit.</p>
        <p>Budget: ${budget.amount}</p>
        <p>Spent: ${budget.calculate_spent_amount()}</p>
        """
        return self.send_email(user.id, subject, html_body)

    def send_monthly_report(self, user_id):
        """Send monthly expense report"""
        user = User.query.get(user_id)
        if not user:
            return False, 'User not found'

        # Would compile monthly statistics here
        subject = "Monthly Expense Report"
        html_body = "<h2>Your Monthly Report</h2><p>Report details...</p>"
        return self.send_email(user.id, subject, html_body)
