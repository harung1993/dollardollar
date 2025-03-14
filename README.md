# 💵 DollarDollar Bill Y'all

An open-source, self-hosted expense tracking and bill-splitting application designed for privacy, flexibility, and financial transparency.


If you like this project and would like to support my work, you can buy me a coffee!! Your support helps me continue creating resources like this one. No pressure at all, and thank you for being here!
<a href="https://buymeacoffee.com/ccfw6gzz28"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=ccfw6gzz28&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" /></a>

## NOTE:
If you are encountering issues after updating/pulling the recent docker, please run:
- `flask db migrate` 
- `flask db upgrade`

If you wish to reset the database
- `python reset.py`


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

### Authentication & Security
- 🔑 Local username/password authentication
- 🔒 OpenID Connect (OIDC) integration for SSO capabilities
- 🛡️ Enterprise-ready authentication with any OIDC provider (Auth0, Okta, Keycloak, etc.)
- 🔐 Password reset and account recovery flows

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
- **Authentication**: Flask-Login, OpenID Connect
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

### OIDC Authentication
- Seamless integration with existing identity providers
- Support for major OIDC providers (Auth0, Okta, Keycloak, etc.)
- Single Sign-On capabilities
- Configuration options:
  - Enable/disable local logins
  - Force OIDC-only authentication
  - Customizable provider name display

### Budget Management
- Set monthly or annual budget targets
- Create category-based budgeting
- Track spending against budget limits
- Get notifications when approaching budget thresholds
- Visualize budget progress with interactive charts

### Advanced Categorization
- Create unlimited custom categories for transactions
- Configure category hierarchies (main categories with sub-categories)
- Auto-categorize transactions based on patterns
- Generate category-based reports for tax purposes
- Compare spending across categories over time

## 🔧 Configuration

### OIDC Setup (Optional)
To enable OpenID Connect authentication:

1. Add the following to your `.env` file:
   ```
   OIDC_ENABLED=True
   OIDC_CLIENT_ID=your_client_id
   OIDC_CLIENT_SECRET=your_client_secret
   OIDC_PROVIDER_NAME=Your Provider Name
   
   # Either use Discovery URL (recommended)
   OIDC_DISCOVERY_URL=https://your-provider/.well-known/openid-configuration
   
   # Or manually configure endpoints
   OIDC_ISSUER=https://your-provider/
   OIDC_AUTH_URI=https://your-provider/auth
   OIDC_TOKEN_URI=https://your-provider/token
   OIDC_USERINFO_URI=https://your-provider/userinfo
   OIDC_LOGOUT_URI=https://your-provider/logout
   ```

2. Optional settings:
   ```
   # Disable password-based logins
   LOCAL_LOGIN_DISABLE=True
   
   # Disable new user registration
   DISABLE_SIGNUPS=True
   ```

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

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

This license requires anyone who runs a modified version of this software, including running it on a server as a service, to make the complete source code available to users of that service.

## 📸 Screenshots

Here's a visual tour of DollarDollar Bill Y'all:

### Dashboard Overview
<img width="1478" alt="Screenshot 2025-03-09 at 10 32 13 PM" src="https://github.com/user-attachments/assets/b1735fba-7181-49e3-b49b-c1cc3a5b4281" />

### Expense Splitting
<img width="1478" alt="Screenshot 2025-03-09 at 10 32 56 PM" src="https://github.com/user-attachments/assets/29f254a0-7773-4050-9251-ed8ba5b4df83" />

### Settling Splits
<img width="1427" alt="Screenshot 2025-03-05 at 10 36 48 PM" src="https://github.com/user-attachments/assets/1ca55758-5390-413b-b8e6-bb85e31263c0" />

### Group Management
<img width="1427" alt="Screenshot 2025-03-05 at 10 24 14 PM" src="https://github.com/user-attachments/assets/33507573-2fb8-4727-9451-509c606bcc91" />

### Multi Currency Support
<img width="1427" alt="Screenshot 2025-03-05 at 10 25 09 PM" src="https://github.com/user-attachments/assets/c965ccc6-4514-4b88-b3d1-7755373bd3ee" />

### Recurring expenses
<img width="1427" alt="Screenshot 2025-03-05 at 10 24 59 PM" src="https://github.com/user-attachments/assets/b0992c09-ea21-4f45-b85d-ce5378fdbdbc" />

### Budgets
<img width="1499" alt="Screenshot 2025-03-13 at 4 15 12 PM" src="https://github.com/user-attachments/assets/b387e51d-53e5-4bd7-80e8-da5c66dfefcd" />
### Categories
<img width="1499" alt="Screenshot 2025-03-13 at 4 15 28 PM" src="https://github.com/user-attachments/assets/23d17592-b440-49f2-a0c5-dca9e8b57b2f" />

## 🙏 Acknowledgements

- Inspired by the need for transparent, flexible expense tracking
- Special thanks to my wife, who endured countless late nights of coding, provided unwavering support, and maintained patience during endless debugging sessions. This project wouldn't exist without her understanding and encouragement.
- Thanks to Jordan Dalby for creating and maintaining the Unraid template
- Thanks to @elmerfds for the OIDC support!


If you like this project and would like to support my work, you can buy me a coffee!! Your support helps me continue creating resources like this one. No pressure at all, and thank you for being here!

<a href="https://buymeacoffee.com/ccfw6gzz28"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=ccfw6gzz28&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" /></a>

