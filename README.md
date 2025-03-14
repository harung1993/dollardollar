# 💵 DollarDollar Bill Y'all

An open-source, self-hosted expense tracking and bill-splitting application designed for privacy, flexibility, and financial transparency.

## NOTE:
If you are encountering issues after updating/pulling the recent docker, please run:
- `flask db migrate` 
- `flask db upgrade`

If you wish to reset the database
- 'Python reset.py'


## 🌟 Why DollarDollar?

Born from a desire to move beyond restrictive financial tracking platforms, this app empowers users with:
- 🔐 Complete control over personal financial data
- 💡 Flexible expense splitting mechanisms
- 🏠 Self-hosted privacy
- 🤝 Collaborative expense management

## 🚀 Key Features

### Expense Tracking
- 📊 Detailed transaction logging
- 💱 Multi-currency support with automatic conversion
- 💳 Multi-card support
- 📅 Date-based expense tracking
- 🔄 Recurring transactions
- 🏷️ Customizable tags for expense categorization

### Splitting Capabilities
- 💸 Multiple split methods:
  - Equal split
  - Custom amount split
  - Percentage-based split
- 👥 Group and personal expense tracking
- 📧 Email invitations for group members

### Financial Insights
- 📆 Monthly financial summaries
- 💰 Comprehensive balance tracking
- 🔍 Detailed transaction filters
- 📈 Expense trends visualization

### Privacy & Control
- 🔒 Self-hosted solution
- 🛡️ No third-party data sharing
- 🔐 Secure user authentication
- 👤 User management
  - Email verification for signup
  - Password recovery
  - Account settings

## 🛠 Tech Stack
- **Backend**: Python, Flask
- **Database**: PostgreSQL
- **Authentication**: Flask-Login
- **Frontend**: Bootstrap, HTML5
- **Deployment**: Docker

## 🚦 Getting Started

### Prerequisites
- Docker
- Docker Compose
- Git

### Quick Installation

1. Clone the repository
   ```bash
   git clone https://github.com/yourusername/dollardollar.git
   cd dollardollar
   ```

2. Configure environment
   ```bash
   cp .env.template .env
   # Edit .env with your configuration
   ```

3. Launch the application
   ```bash
   docker-compose up -d
   ```

4. Access the app at `http://localhost:5006`

## 💼 Usage

### Recurring Transactions
Set up transactions that repeat on a regular schedule:
- Daily, weekly, monthly, or yearly recurrence
- Set end dates or number of occurrences
- Edit or cancel recurring transactions

### Multi-Currency Support
- Add expenses in any currency
- Automatic conversion based on current exchange rates
- View totals in your preferred currency
- Historical exchange rate tracking

### Tagging System
- Create custom tags for expense categorization
- Filter and search expenses by tags
- Analyze spending patterns by category
- Tag-based reports and visualization

### User Management
- Secure signup with email verification
- Add users to groups via email invitations
- User role management within groups
- Account recovery via password reset

## 🤝 Development Approach

This project explores AI-assisted open-source development:
- Leveraging AI tools for rapid prototyping
- Combining technological innovation with human creativity
- Iterative development with large language models
  - Local LLMs (qwen2.5, DeepSeek-V3)
  - Claude AI
  - Human domain expertise

## 🤲 Contributing

Contributions are welcome! Please check out our contributing guidelines.

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📜 License

MIT License

## 📸 Screenshots

Here's a visual tour of DollarDollar Bill Y'all:

### Dashboard Overview
<img width="1478" alt="Screenshot 2025-03-09 at 10 32 13 PM" src="https://github.com/user-attachments/assets/b1735fba-7181-49e3-b49b-c1cc3a5b4281" />

### Expense Splitting
<img width="1478" alt="Screenshot 2025-03-09 at 10 32 56 PM" src="https://github.com/user-attachments/assets/29f254a0-7773-4050-9251-ed8ba5b4df83" />

### Settling Splits
<img width="1427" alt="Screenshot 2025-03-05 at 10 36 48 PM" src="https://github.com/user-attachments/assets/1ca55758-5390-413b-b8e6-bb85e31263c0" />

### Group Management
<img width="1427" alt="Screenshot 2025-03-05 at 10 24 14 PM" src="https://github.com/user-attachments/assets/33507573-2fb8-4727-9451-509c606bcc91" />

### Muti Currency Support
<img width="1427" alt="Screenshot 2025-03-05 at 10 25 09 PM" src="https://github.com/user-attachments/assets/c965ccc6-4514-4b88-b3d1-7755373bd3ee" />

### Recurring expenses
<img width="1427" alt="Screenshot 2025-03-05 at 10 24 59 PM" src="https://github.com/user-attachments/assets/b0992c09-ea21-4f45-b85d-ce5378fdbdbc" />

## 🙏 Acknowledgements

- Inspired by the need for transparent, flexible expense tracking
- Special thanks to my wife, who endured countless late nights of coding, provided unwavering support, and maintained patience during endless debugging sessions. This project wouldn't exist without her understanding and encouragement.
