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

# FinPal is Now Live for Community Testing

**DollarDollar has evolved into FinPal** as part of the PalStack ecosystem. This represents a complete architectural modernization with enhanced features and deployment flexibility for both self-hosted and managed hosting scenarios.

## About PalStack

> *"That's what pals do – they show up and help with the everyday stuff."*

PalStack is a family of applications designed to simplify daily life management. FinPal (formerly DollarDollar) is our financial management component, focused on making personal finance tracking effortless and privacy-respecting.

## Current Status

- **Backend**: Production-ready microservices architecture
- **Web UI**: Live and ready for testing at finpal.palstack.io
- **Mobile Apps**: Beta testing in progress
- **Licensing**: Dual licensed (AGPL-3.0 for personal use, commercial license available)

## Key Improvements

- Modular microservices backend for better scalability
- Modern React-based frontend with improved UX
- Native mobile applications in active development
- Self-hosted first, with optional managed hosting
- Dynamic branding based on default currency (DollarPal, EuroPal, RupeePal, etc.)

## Roadmap Highlights

- Rollover budgets for flexible period management
- Enhanced sync engine with improved reliability
- Advanced analytics and financial insights
- Streamlined group bill-splitting workflows
- Additional features in development pipeline

## Testing and Feedback

We're opening this up to the community first. The beta is available via Docker Hub, with full documentation at [finpal.palstack.io](https://finpal.palstack.io). Bug reports, feature requests, and feedback are critical as we work toward our February 2026 public launch.

## Repository Status

This repository is preserved for historical reference. Active development continues in the FinPal Core repository under the PalStack organization.

<p align="center">An open-source, self-hosted money management platform with comprehensive expense tracking, budgeting, account synchronization, and bill-splitting features - designed for privacy, flexibility, and complete financial control.</p>
<div align="center">
  <h3>
    <a href="https://ddby.finforward.xyz">Demo</a>
    <a>|</a>
    <a href="https://discord.gg/7Z2EqVZYqm">Discord</a>
    <a>|</a>
    <a href="license.txt">License</a>
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
- 💼 **Track Portfolios and investments with auto update of sticker prices

  
## 🚀 Features

- **💰 Expense Tracking & Management**
  - Multi-currency support with automatic conversion
  - Recurring transactions with flexible scheduling
  - Auto-categorization with customizable rules
  - Transaction importing (CSV, SimpleFin)
  - Transaction with multi category support
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
- **💼 Portfolio Management
  - Create and manage multiple investment portfolios
  - Link portfolios to accounts for automatic balance updates
  - Track individual investments across different portfolios
  - Visualize portfolio performance and distribution
 
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
   git clone https://github.com/harung1993/dollardollar.git
   cd dollardollar
   ```

2. Configure environment
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. Launch the application
   ```bash
   docker-compose up -d
   ```

4. Access the app at `http://localhost:5006`

## ⚙️ Configuration Options

### Investment Tracking (Optional)
To enable Investment Tracking :
```
INVESTMENT_TRACKING_ENABLED=True
```

### OIDC Setup (Optional)
To enable OpenID Connect authentication:

```
OIDC_ENABLED=True
OIDC_CLIENT_ID=your_client_id
OIDC_CLIENT_SECRET=your_client_secret
OIDC_PROVIDER_NAME=Your Provider Name
OIDC_DISCOVERY_URL=https://your-provider/.well-known/openid-configuration
```
### Other Optionals
# Optional settings
```
LOCAL_LOGIN_DISABLE=True  # Disable password logins
DISABLE_SIGNUPS=True      # Disable registration
```

### Additional Configuration
For detailed configuration options, see the [.env.template](https://github.com/harung1993/dollardollar/blob/main/.env.example) file.

## 📸 Screenshots

<div align="center">
  <img width="45%" alt="Dashboard" src="https://github.com/user-attachments/assets/32542178-011c-4043-801f-75d50f773cf1" />
  <img width="45%" alt="Expense Splitting" src="https://github.com/user-attachments/assets/29f254a0-7773-4050-9251-ed8ba5b4df83" />
  <img width="45%" alt="Settling Splits" src="https://github.com/user-attachments/assets/1ca55758-5390-413b-b8e6-bb85e31263c0" />
  <img width="45%" alt="Budgets" src="https://github.com/user-attachments/assets/8db5c16b-37e4-4bf4-aa0e-396810e0380d" />
  <img width="45%" alt="Categories" src="https://github.com/user-attachments/assets/23d17592-b440-49f2-a0c5-dca9e8b57b2f" />
  <img width="45%" alt="Portfolios" src="https://github.com/user-attachments/assets/d20c5142-9261-413e-ae45-7588b21917d4" />

</div>

## 🤝 Development Approach

This project explores AI-assisted open-source development:
- Leveraging AI tools for rapid prototyping
- Combining technological innovation with human creativity
- Iterative development with large language models
  - Local LLMs (qwen2.5, DeepSeek-V3)
  - Claude AI
  - Human domain expertise
  
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

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](license.txt) file for details.

This license requires anyone who runs a modified version of this software, including running it on a server as a service, to make the complete source code available to users of that service.

## 🙏 Support

If you like this project and would like to support my work, you can buy me a coffee!

<a href="https://buymeacoffee.com/ccfw6gzz28"><img src="https://img.buymeacoffee.com/button-api/?text=Buy me a coffee&emoji=&slug=ccfw6gzz28&button_colour=FFDD00&font_colour=000000&font_family=Cookie&outline_colour=000000&coffee_colour=ffffff" /></a>
