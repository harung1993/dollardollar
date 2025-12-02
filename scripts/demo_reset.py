# demo_reset.py
import os
import time
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import schedule

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('demo_reset')

# Get database URI from environment variable
DB_URI = os.getenv('SQLALCHEMY_DATABASE_URI')
RESET_INTERVAL = int(os.getenv('RESET_INTERVAL', 86400))  # Default: 24 hours

def reset_demo_data():
    """Reset the demo database to a clean state with sample data"""
    logger.info("Starting demo environment reset")
    
    try:
        # Create database engine
        engine = create_engine(DB_URI)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Import models for database operations
        from app import User, Group, Expense, Budget, Category, Tag
        
        # Clean demo-specific data
        logger.info("Cleaning demo user data")
        
        # Get all demo users (email contains 'demo')
        demo_users = session.query(User).filter(User.id.like('%demo%')).all()
        
        for user in demo_users:
            # Delete all user's expenses
            logger.info(f"Deleting expenses for user: {user.id}")
            session.query(Expense).filter(Expense.user_id == user.id).delete()
            
            # Delete user's budgets
            logger.info(f"Deleting budgets for user: {user.id}")
            session.query(Budget).filter(Budget.user_id == user.id).delete()
            
            # Delete user's tags
            logger.info(f"Deleting tags for user: {user.id}")
            session.query(Tag).filter(Tag.user_id == user.id).delete()
            
            # Find groups created by user
            logger.info(f"Deleting groups for user: {user.id}")
            user_groups = session.query(Group).filter(Group.created_by == user.id).all()
            for group in user_groups:
                session.delete(group)
        
        # Reset demo user passwords
        for user in demo_users:
            logger.info(f"Resetting password for user: {user.id}")
            user.set_password('demo')
        
        # Commit changes
        session.commit()
        
        # Recreate demo data
        logger.info("Recreating demo data")
        from app import create_demo_data
        
        for user in demo_users:
            create_demo_data(user.id)
        
        logger.info("Demo environment reset completed successfully")
        
    except Exception as e:
        logger.error(f"Error during demo reset: {str(e)}")
        if session:
            session.rollback()
    finally:
        if session:
            session.close()

def main():
    """Main function that schedules and runs the reset job"""
    logger.info("Demo reset service starting")
    
    # Run reset immediately at startup
    reset_demo_data()
    
    # Schedule reset based on interval
    hours = RESET_INTERVAL / 3600
    logger.info(f"Scheduling reset every {hours} hours")
    
    schedule.every(RESET_INTERVAL).seconds.do(reset_demo_data)
    
    # Run the schedule loop
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main()