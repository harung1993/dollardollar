<p align="center">
  <a href="https://github.com/yourusername/dollardollar">
    <img src=https://github.com/harung1993/dollardollar/blob/main/static/images/dddby.png alt="DollarDollar Bill Y'all logo" width="200" />
  </a>
</p>
<h1 align="center">DollarDollar Bill Y'all</h1>
<div align="center">
<a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-blue.svg" alt="license"></a>
<a href="https://github.com/harung1993/dollardollar/actions"><img src="https://img.shields.io/github/actions/workflow/status/harung1993/dollardollar/ci.yml?branch=main" alt="GitHub Workflow Status"></a>
</div>
<p align="center">An open-source, self-hosted money management platform with comprehensive expense tracking, budgeting, account synchronization, and bill-splitting features - designed for privacy, flexibility, and complete financial control.</p>
<div align="center">
  <h3>
    <a href="https://ddby.finforward.xyz">Demo</a>
    <a>|</a>
    <a href="https://discord.gg/7Z2EqVZYqm">Discord</a>
  </h3>
</div>

## 🌟 Why DollarDollar?

Born from a desire to move beyond restrictive financial tracking platforms, this app empowers users with:

- 🔐 **Complete control over personal financial data**
- 💡 **Flexible expense splitting mechanisms**
- 🏠 **Self-hosted privacy**
- 🤝 **Collaborative expense management**
- 🔄 **Integration with Simplefin** (auto tracking accounts and transactions)
- 💰 **Budgets with notifications**
- 🖥️ **Seamless integration with Unraid** for easy installation and management via Unraid templates

  
## 🚀 Features

- **💰 Expense Tracking & Management**
  - Multi-currency support with automatic conversion
  - Recurring transactions with flexible scheduling
  - Auto-categorization with customizable rules
  - Transaction importing (CSV, SimpleFin)
  - Multi-card and multi-account support
  - Date-based expense tracking

- **👥 Bill Splitting**
  - Multiple split methods: equal, custom amount, percentage
  - Group and personal expense tracking
  - Settlement tracking and balances
  - Email invitations for group members

- **📊 Budgeting & Analytics**
  - Custom budgets with notifications
  - Monthly financial summaries
  - Expense trends visualization
  - Category-based spending analysis
  - Comprehensive balance tracking

- **🏷️ Organization & Categories**
  - Customizable tags for expense categorization
  - Category hierarchies (main categories with sub-categories)
  - Auto-categorization based on transaction patterns
  - Category-based reports for tax purposes

- **🔐 Security & Privacy**
  - Self-hosted for complete data control
  - Local auth + OpenID Connect (OIDC) integration
  - Enterprise-ready authentication with any OIDC provider
  - User management with password recovery
  - No third-party data sharing

## 🛠️ Getting Started

### Updating
If you are encountering issues after updating/pulling the recent docker, please run:
```bash
flask db migrate
flask db upgrade
```

If you wish to reset the database:
```bash
python reset.py
```

### Prerequisites
- Docker
- Docker Compose

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

## ⚙️ Configuration Options

### OIDC Setup (Optional)
To enable OpenID Connect authentication:

```
OIDC_ENABLED=True
OIDC_CLIENT_ID=your_client_id
OIDC_CLIENT_SECRET=your_client_secret
OIDC_PROVIDER_NAME=Your Provider Name
OIDC_DISCOVERY_URL=https://your-provider/.well-known/openid-configuration

# Optional settings
LOCAL_LOGIN_DISABLE=True  # Disable password logins
DISABLE_SIGNUPS=True      # Disable registration
```

### Additional Configuration
For detailed configuration options, see the [.env.template](https://github.com/yourusername/dollardollar/blob/main/.env.template) file.

## 📸 Screenshots

<div align="center">
  <img width="45%" alt="Dashboard" src="https://github.com/user-attachments/assets/32542178-011c-4043-801f-75d50f773cf1" />
  <img width="45%" alt="Expense Splitting" src="https://github.com/user-attachments/assets/29f254a0-7773-4050-9251-ed8ba5b4df83" />
  <img width="45%" alt="Settling Splits" src="https://github.com/user-attachments/assets/1ca55758-5390-413b-b8e6-bb85e31263c0" />
  <img width="45%" alt="Budgets" src="https://github.com/user-attachments/assets/8db5c16b-37e4-4bf4-aa0e-396810e0380d" />
  <img width="45%" alt="Categories" src="https://github.com/user-attachments/assets/23d17592-b440-49f2-a0c5-dca9e8b57b2f" />
</div>

## 🤝 Contributing

Contributions are welcome! Please check out our contributing guidelines.

1. Fork the repository
2. Create your feature branch
3. Submit a Pull Request

## 🙏 Acknowledgements

- Special thanks to my wife, who endured countless late nights of coding, provided unwavering support, and maintained patience during endless debugging sessions
- Thanks to JordanDalby for creating and maintaining the Unraid template
- Thanks to @elmerfds for the OIDC support!
  
## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

This license requires anyone who runs a modified version of this software, including running it on a server as a service, to make the complete source code available to users of that service.

## 🙏 Support

If you like this project and would like to support my work, you can buy me a coffee!

<a href="https://buymeacoffee.com/ccfw6gzz28"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=ccfw6gzz28&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" /></a>
