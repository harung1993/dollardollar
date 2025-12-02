# DollarDollar Frontend Revamp Plan
## React Native with Expo - Mobile & Web Cross-Platform

**Date**: December 2, 2025
**Status**: 📋 Planning Phase
**Goal**: Migrate from Flask templates to React Native with Expo for unified mobile and web experience

---

## 🎯 Project Overview

### Vision
Transform DollarDollar from a traditional Flask template-based app into a modern cross-platform application using React Native with Expo, sharing a single codebase between:
- 📱 **iOS Mobile App**
- 🤖 **Android Mobile App**
- 🌐 **Web Application**

### Design Philosophy
Based on the provided HTML mockup, the new design will feature:
- **Dark theme** with green accent colors (`#15803d` primary)
- **Glassmorphism** UI with blur effects and transparency
- **Floating dollar symbols** in background (subtle animation)
- **Modern card-based** layout with hover effects
- **Sidebar navigation** with collapsible menu
- **Minimalist** and clean interface
- **Smooth animations** and transitions

---

## 📊 Current State Analysis

### Existing Architecture
```
Backend (Flask):
├── src/
│   ├── services/          # Modular services (analytics, auth, account, etc.)
│   ├── models/            # SQLAlchemy ORM models
│   ├── utils/             # Helper functions
│   └── extensions.py      # Flask extensions

Frontend (Current):
├── templates/             # 40+ Jinja2 templates
│   ├── base.html         # Base template with sidebar
│   ├── dashboard.html    # Main dashboard
│   ├── transactions.html # Transaction management
│   ├── accounts.html     # Account management
│   ├── budgets.html      # Budget tracking
│   ├── groups.html       # Group bill splitting
│   └── ... (34+ more pages)
│
├── static/
│   ├── css/              # 3 CSS files
│   │   ├── styles.css
│   │   ├── transaction-module.css
│   │   └── investment-charts.css
│   └── js/               # 30+ JavaScript files
│       ├── dashboard/
│       ├── transactions/
│       ├── budget/
│       └── ...
```

### Current Pages to Migrate
1. **Dashboard** - Main overview with metrics, charts, categories
2. **Transactions** - List, add, edit, filter transactions
3. **Accounts** - Account management with balances
4. **Budgets** - Budget creation and tracking
5. **Categories** - Category management
6. **Groups** - Group management and bill splitting
7. **Settlements** - Settlement tracking
8. **Recurring** - Recurring transaction management
9. **Statistics** - Charts and analytics
10. **Tags** - Tag management
11. **Currencies** - Currency management
12. **Category Mappings** - Auto-categorization rules
13. **Advanced** - SimpleFin integration settings
14. **Profile** - User profile management

### Backend API Readiness
Currently, the Flask backend renders templates. We need to:
- ✅ Service layer already exists (good for API conversion)
- ✅ Modular architecture in place
- ❌ Need to create REST API endpoints
- ❌ Need API authentication (JWT)
- ❌ Need CORS configuration

---

## 🏗️ Proposed Architecture

### Three-Tier Architecture

```
┌─────────────────────────────────────────────────┐
│         React Native + Expo (Frontend)          │
│  ┌──────────────┬──────────────┬──────────────┐ │
│  │  iOS App     │  Android App │   Web App    │ │
│  └──────────────┴──────────────┴──────────────┘ │
│         Shared React Native Components          │
└─────────────────────────────────────────────────┘
                        ↕ REST API
┌─────────────────────────────────────────────────┐
│          Flask REST API (Backend)               │
│  ┌──────────────────────────────────────────┐   │
│  │  API Endpoints (JSON responses)          │   │
│  │  - /api/dashboard                        │   │
│  │  - /api/transactions                     │   │
│  │  - /api/accounts                         │   │
│  │  - /api/budgets                          │   │
│  │  └─ ... (all existing services)          │   │
│  └──────────────────────────────────────────┘   │
│         Existing Service Layer ✅                │
└─────────────────────────────────────────────────┘
                        ↕
┌─────────────────────────────────────────────────┐
│              PostgreSQL Database                │
│         (Existing schema - no changes)          │
└─────────────────────────────────────────────────┘
```

---

## 📱 Technology Stack

### Frontend
- **Framework**: React Native 0.74+
- **Platform**: Expo SDK 51+
- **Navigation**: React Navigation 6
- **State Management**:
  - React Query (server state)
  - Zustand (client state)
- **Styling**:
  - Styled Components / React Native StyleSheet
  - React Native Reanimated (animations)
- **Charts**: Victory Native or React Native Chart Kit
- **Forms**: React Hook Form
- **UI Components**: Custom components based on design system
- **Icons**: Expo Vector Icons

### Backend API
- **Framework**: Flask (existing)
- **API Format**: REST JSON
- **Authentication**: JWT (Flask-JWT-Extended)
- **Serialization**: Marshmallow schemas
- **CORS**: Flask-CORS
- **API Documentation**: Flask-RESTX or OpenAPI

### Development Tools
- **Package Manager**: npm or yarn
- **Linting**: ESLint with React Native config
- **Formatting**: Prettier
- **TypeScript**: Optional but recommended
- **Testing**: Jest + React Native Testing Library

---

## 🎨 Design System

### Color Palette (from mockup)
```javascript
const colors = {
  primary: {
    green: '#15803d',
    greenLight: '#16a34a',
  },
  background: {
    primary: '#0a0a0a',
    surface: 'rgba(255, 255, 255, 0.03)',
    surfaceHover: 'rgba(255, 255, 255, 0.06)',
  },
  border: {
    default: 'rgba(255, 255, 255, 0.08)',
    hover: 'rgba(255, 255, 255, 0.12)',
  },
  text: {
    primary: '#ffffff',
    secondary: '#a3a3a3',
    tertiary: '#666666',
  },
  accent: {
    red: '#ef4444',
    green: '#10b981',
    gold: '#fbbf24',
  },
};
```

### Typography
```javascript
const typography = {
  hero: {
    fontSize: 40,
    fontWeight: '600',
    letterSpacing: -0.8,
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
  },
  body: {
    fontSize: 16,
    lineHeight: 1.6,
  },
  caption: {
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
};
```

### Component Patterns
1. **Glassmorphism Cards**
   - Transparent background with blur
   - Border with low opacity
   - Hover effects with glow

2. **Sidebar Navigation**
   - Collapsible sidebar
   - Active state highlighting
   - Icon + text layout

3. **Metric Cards**
   - Large numbers with labels
   - Trend indicators (↑↓)
   - Hover animations

4. **Floating Action Button (FAB)**
   - Fixed position bottom-right
   - Primary action (Add transaction)
   - Rotate animation on hover

---

## 🗂️ Project Structure

```
dollardollar/
├── backend/                    # Flask backend (existing src/)
│   ├── src/                   # Existing modular services
│   ├── api/                   # NEW - REST API endpoints
│   │   ├── __init__.py
│   │   ├── auth.py           # JWT authentication
│   │   ├── dashboard.py      # Dashboard API
│   │   ├── transactions.py   # Transactions API
│   │   ├── accounts.py       # Accounts API
│   │   ├── budgets.py        # Budgets API
│   │   └── ... (all services)
│   ├── schemas/               # NEW - Marshmallow schemas
│   │   ├── transaction.py
│   │   ├── account.py
│   │   └── ...
│   └── app.py                # Updated with API blueprints
│
├── frontend/                  # NEW - React Native app
│   ├── app/                  # Expo Router (file-based routing)
│   │   ├── (auth)/           # Auth screens
│   │   │   ├── login.tsx
│   │   │   └── signup.tsx
│   │   ├── (tabs)/           # Main app tabs
│   │   │   ├── _layout.tsx
│   │   │   ├── dashboard.tsx
│   │   │   ├── transactions.tsx
│   │   │   ├── accounts.tsx
│   │   │   ├── budgets.tsx
│   │   │   └── more.tsx
│   │   ├── _layout.tsx       # Root layout
│   │   └── index.tsx         # Entry point
│   │
│   ├── src/
│   │   ├── components/       # Reusable components
│   │   │   ├── common/       # Buttons, Cards, Inputs
│   │   │   ├── navigation/   # Sidebar, Header, TabBar
│   │   │   ├── charts/       # Chart components
│   │   │   ├── forms/        # Form components
│   │   │   └── layouts/      # Layout wrappers
│   │   │
│   │   ├── screens/          # Screen components
│   │   │   ├── Dashboard/
│   │   │   ├── Transactions/
│   │   │   ├── Accounts/
│   │   │   └── ...
│   │   │
│   │   ├── hooks/            # Custom React hooks
│   │   │   ├── useAuth.ts
│   │   │   ├── useTransactions.ts
│   │   │   ├── useAccounts.ts
│   │   │   └── ...
│   │   │
│   │   ├── services/         # API service layer
│   │   │   ├── api.ts        # Axios configuration
│   │   │   ├── auth.ts       # Auth API calls
│   │   │   ├── transactions.ts
│   │   │   └── ...
│   │   │
│   │   ├── store/            # State management
│   │   │   ├── authStore.ts  # Auth state (Zustand)
│   │   │   └── appStore.ts   # App-wide state
│   │   │
│   │   ├── theme/            # Design system
│   │   │   ├── colors.ts
│   │   │   ├── typography.ts
│   │   │   ├── spacing.ts
│   │   │   └── shadows.ts
│   │   │
│   │   ├── types/            # TypeScript types
│   │   │   ├── api.ts
│   │   │   ├── models.ts
│   │   │   └── navigation.ts
│   │   │
│   │   └── utils/            # Utility functions
│   │       ├── currency.ts
│   │       ├── date.ts
│   │       └── formatting.ts
│   │
│   ├── assets/               # Images, fonts, icons
│   ├── app.json              # Expo configuration
│   ├── package.json
│   ├── tsconfig.json
│   └── babel.config.js
│
├── docker-compose.yml        # Updated for API + Frontend
└── README.md                 # Updated documentation
```

---

## 🔄 Migration Strategy

### Phase 1: Backend API Layer (Week 1-2)
**Goal**: Create REST API without breaking existing template-based app

#### Tasks:
1. **Setup API Blueprint Structure**
   - Create `backend/api/` folder
   - Setup Flask-RESTX or Flask-RESTful
   - Configure CORS for development

2. **Implement JWT Authentication**
   - Install Flask-JWT-Extended
   - Create `/api/auth/login` endpoint
   - Create `/api/auth/register` endpoint
   - Create `/api/auth/refresh` endpoint
   - Add JWT decorator for protected routes

3. **Create Marshmallow Schemas**
   - TransactionSchema
   - AccountSchema
   - BudgetSchema
   - CategorySchema
   - UserSchema
   - GroupSchema

4. **Convert Service Layer to API Endpoints**
   - **Analytics API** (`/api/analytics/`)
     - `GET /dashboard` - Dashboard data
     - `GET /stats` - Statistics data
     - `GET /trends` - Spending trends

   - **Transactions API** (`/api/transactions/`)
     - `GET /` - List transactions (with filters)
     - `POST /` - Create transaction
     - `GET /:id` - Get transaction details
     - `PUT /:id` - Update transaction
     - `DELETE /:id` - Delete transaction
     - `GET /recent` - Recent transactions

   - **Accounts API** (`/api/accounts/`)
     - `GET /` - List accounts
     - `POST /` - Create account
     - `GET /:id` - Get account details
     - `PUT /:id` - Update account
     - `DELETE /:id` - Delete account
     - `GET /:id/balance` - Get account balance

   - **Budgets API** (`/api/budgets/`)
     - `GET /` - List budgets
     - `POST /` - Create budget
     - `GET /:id` - Get budget details
     - `PUT /:id` - Update budget
     - `DELETE /:id` - Delete budget
     - `GET /:id/progress` - Get budget progress

   - **Categories API** (`/api/categories/`)
   - **Groups API** (`/api/groups/`)
   - **Recurring API** (`/api/recurring/`)
   - **Currencies API** (`/api/currencies/`)
   - **Tags API** (`/api/tags/`)

5. **API Testing**
   - Setup Postman/Insomnia collection
   - Test all endpoints
   - Document API responses

#### Deliverables:
- ✅ Fully functional REST API
- ✅ JWT authentication working
- ✅ API documentation
- ✅ Postman collection
- ⚠️ Existing Flask templates still work (no breaking changes)

---

### Phase 2: React Native Setup & Core Components (Week 2-3)
**Goal**: Setup Expo project with design system and core components

#### Tasks:
1. **Initialize Expo Project**
   ```bash
   cd dollardollar
   npx create-expo-app@latest frontend --template blank-typescript
   cd frontend
   npx expo install expo-router react-native-safe-area-context react-native-screens
   ```

2. **Install Dependencies**
   ```bash
   npm install @react-navigation/native @react-navigation/native-stack
   npm install axios react-query zustand
   npm install react-hook-form
   npm install @expo/vector-icons
   npm install react-native-reanimated react-native-gesture-handler
   npm install victory-native
   ```

3. **Configure Expo Router**
   - Setup file-based routing
   - Create layout files
   - Configure navigation structure

4. **Create Design System**
   - `theme/colors.ts` - Color constants
   - `theme/typography.ts` - Font styles
   - `theme/spacing.ts` - Spacing constants
   - `theme/shadows.ts` - Shadow/elevation styles

5. **Build Core Components**
   - **Layout Components**
     - `AppLayout` - Main app wrapper
     - `Sidebar` - Collapsible sidebar navigation
     - `Header` - Top header bar
     - `BottomTabBar` - Mobile bottom navigation

   - **Common Components**
     - `Button` - Primary, secondary, outline variants
     - `Card` - Glassmorphism card with hover
     - `Input` - Text input with validation
     - `Select` - Dropdown selector
     - `Modal` - Modal dialog
     - `LoadingSpinner` - Loading indicator
     - `ErrorBoundary` - Error handling

   - **Specific Components**
     - `MetricCard` - Dashboard metric card
     - `CategoryCard` - Category spending card
     - `TransactionItem` - Transaction list item
     - `AccountCard` - Account balance card
     - `BudgetProgress` - Budget progress bar
     - `FAB` - Floating action button

6. **Setup API Service Layer**
   - Configure Axios with base URL
   - Add request/response interceptors
   - Implement token refresh logic
   - Create API service modules

7. **Setup State Management**
   - Configure React Query
   - Create Zustand stores (auth, app)
   - Implement custom hooks

#### Deliverables:
- ✅ Expo project initialized
- ✅ Design system implemented
- ✅ Core components built
- ✅ API service layer configured
- ✅ State management setup

---

### Phase 3: Authentication & Navigation (Week 3-4)
**Goal**: Implement auth flow and navigation structure

#### Tasks:
1. **Build Auth Screens**
   - Login screen
   - Signup screen
   - Password reset screen
   - Loading/splash screen

2. **Implement Auth Flow**
   - JWT token storage (SecureStore)
   - Login functionality
   - Logout functionality
   - Token refresh
   - Protected routes

3. **Build Navigation Structure**
   - Bottom tabs for mobile (Dashboard, Transactions, Accounts, Budgets, More)
   - Sidebar for web/tablet
   - Modal stack for forms
   - Deep linking configuration

4. **Implement User Context**
   - User profile state
   - Authentication state
   - App preferences (theme, currency)

#### Deliverables:
- ✅ Auth screens functional
- ✅ JWT authentication working
- ✅ Navigation structure complete
- ✅ Protected routes implemented

---

### Phase 4: Dashboard Screen (Week 4-5)
**Goal**: Build the main dashboard matching the design mockup

#### Tasks:
1. **Dashboard Layout**
   - Hero section with greeting
   - Metrics grid (4 cards)
   - Financial overview chart
   - Top spending categories

2. **Metric Cards**
   - Monthly Spending
   - Net Balance (IOU data)
   - Total Assets
   - Budget Remaining
   - With trend indicators

3. **Chart Integration**
   - Setup Victory Native
   - Spending trends line chart
   - Category breakdown chart
   - Interactive tooltips

4. **Category Cards Grid**
   - Icon, name, transaction count
   - Amount and percentage
   - Tap to filter transactions

5. **FAB for Quick Actions**
   - Add transaction
   - Add income
   - Add transfer

#### Deliverables:
- ✅ Dashboard screen complete
- ✅ All metrics displaying
- ✅ Charts rendering
- ✅ Interactive elements working

---

### Phase 5: Transactions Management (Week 5-6)
**Goal**: Build transaction list, add, edit, and filter

#### Tasks:
1. **Transaction List**
   - Infinite scroll/pagination
   - Pull-to-refresh
   - Search and filters
   - Group by date

2. **Transaction Forms**
   - Add transaction modal
   - Edit transaction modal
   - Multi-category support
   - Split with users
   - Recurring transaction setup

3. **Transaction Details**
   - View full details
   - Edit/delete actions
   - Split breakdown
   - Category assignment

4. **Filters & Search**
   - Date range picker
   - Category filter
   - Account filter
   - Amount range
   - Search by description

#### Deliverables:
- ✅ Transaction list working
- ✅ Add/edit forms functional
- ✅ Filters implemented
- ✅ Search working

---

### Phase 6: Accounts & Budgets (Week 6-7)
**Goal**: Build account management and budget tracking

#### Tasks:
1. **Accounts Screen**
   - Account list with balances
   - Add/edit account forms
   - Account details view
   - Transaction history per account
   - SimpleFin sync status

2. **Budgets Screen**
   - Budget list with progress bars
   - Add/edit budget forms
   - Budget details with spending breakdown
   - Alert notifications
   - Category-based budgets

#### Deliverables:
- ✅ Accounts screen complete
- ✅ Budgets screen complete
- ✅ Forms working
- ✅ Progress tracking functional

---

### Phase 7: Groups, Categories & Settings (Week 7-8)
**Goal**: Complete remaining core features

#### Tasks:
1. **Groups & Bill Splitting**
   - Group list
   - Create/edit group
   - Add members
   - Group expenses
   - Settlement tracking
   - Balance calculations

2. **Categories Management**
   - Category list
   - Create/edit categories
   - Category icons
   - Category mappings (auto-categorization)

3. **Settings & Profile**
   - User profile
   - Currency preferences
   - Notification settings
   - Security settings
   - Theme preferences

4. **Additional Screens**
   - Recurring transactions
   - Statistics/reports
   - Tags management
   - Currencies list

#### Deliverables:
- ✅ Groups screen complete
- ✅ Categories screen complete
- ✅ Settings screen complete
- ✅ All core features functional

---

### Phase 8: Polish & Optimization (Week 8-9)
**Goal**: Animations, performance, and UX improvements

#### Tasks:
1. **Animations**
   - Implement React Native Reanimated
   - Floating dollar background animation
   - Card hover effects (web)
   - Page transitions
   - Loading states
   - Success/error toasts

2. **Performance Optimization**
   - Optimize re-renders
   - Implement virtualized lists
   - Image optimization
   - Code splitting
   - Lazy loading

3. **Responsive Design**
   - Mobile layout (< 768px)
   - Tablet layout (768px - 1024px)
   - Desktop layout (> 1024px)
   - Sidebar behavior per breakpoint

4. **Error Handling**
   - Network error handling
   - Form validation errors
   - Empty states
   - Error boundaries
   - Retry mechanisms

5. **Accessibility**
   - Screen reader support
   - Keyboard navigation
   - Focus management
   - ARIA labels
   - Color contrast

#### Deliverables:
- ✅ Smooth animations
- ✅ Performance optimized
- ✅ Fully responsive
- ✅ Error handling complete
- ✅ Accessible

---

### Phase 9: Testing & Deployment (Week 9-10)
**Goal**: Test thoroughly and deploy

#### Tasks:
1. **Testing**
   - Unit tests for components
   - Integration tests for API
   - E2E tests for critical flows
   - Cross-platform testing
   - Performance testing

2. **Build & Deploy**
   - Configure app.json for production
   - Setup EAS Build
   - Build iOS app
   - Build Android app
   - Build web version
   - Deploy to app stores (optional)
   - Deploy web version

3. **Documentation**
   - Update README
   - API documentation
   - User guide
   - Developer guide
   - Contribution guidelines

#### Deliverables:
- ✅ All tests passing
- ✅ Apps built and deployed
- ✅ Documentation complete
- ✅ Production ready

---

## 🚀 Implementation Approach

### Parallel Development
- **Backend API** and **Frontend** can be developed in parallel
- Use mock data initially for frontend development
- Backend team focuses on API endpoints
- Frontend team focuses on UI components

### Incremental Rollout
1. **Phase 1-3**: Internal testing with team
2. **Phase 4-6**: Beta testing with select users
3. **Phase 7-9**: Full rollout to all users
4. **Maintain templates**: Keep Flask templates as fallback during transition

### Data Migration
- ✅ No database changes needed
- ✅ Existing data works as-is
- ✅ No downtime required
- ✅ Gradual user migration

---

## 📦 Key Dependencies

### Backend (New)
```
flask-jwt-extended==4.6.0
flask-cors==4.0.0
marshmallow==3.21.0
flask-restx==1.3.0  # or flask-restful
```

### Frontend (New)
```json
{
  "dependencies": {
    "expo": "~51.0.0",
    "expo-router": "~3.5.0",
    "react": "18.2.0",
    "react-native": "0.74.0",
    "@react-navigation/native": "^6.1.0",
    "axios": "^1.6.0",
    "@tanstack/react-query": "^5.0.0",
    "zustand": "^4.5.0",
    "react-hook-form": "^7.50.0",
    "victory-native": "^36.0.0",
    "react-native-reanimated": "~3.10.0",
    "react-native-gesture-handler": "~2.16.0",
    "expo-secure-store": "~13.0.0"
  }
}
```

---

## 🎯 Success Criteria

### Functionality
- ✅ All existing features working in new frontend
- ✅ Feature parity with Flask templates
- ✅ Cross-platform consistency

### Performance
- ✅ App loads in < 3 seconds
- ✅ Smooth 60fps animations
- ✅ API response times < 500ms

### User Experience
- ✅ Intuitive navigation
- ✅ Responsive on all screen sizes
- ✅ Accessible to all users
- ✅ Beautiful, modern design

### Technical
- ✅ Clean, maintainable code
- ✅ Good test coverage (>80%)
- ✅ Well-documented
- ✅ Easy to extend

---

## ⚠️ Risks & Mitigation

### Risk 1: API Performance
**Risk**: API might be slower than server-side rendering
**Mitigation**:
- Implement caching with React Query
- Optimize database queries
- Use pagination/lazy loading
- CDN for static assets

### Risk 2: Learning Curve
**Risk**: Team unfamiliar with React Native
**Mitigation**:
- Start with training/tutorials
- Pair programming
- Code reviews
- Gradual complexity increase

### Risk 3: Native App Store Approval
**Risk**: App stores might reject the app
**Mitigation**:
- Follow platform guidelines
- Use Expo's managed workflow
- Test thoroughly before submission
- Have web version as backup

### Risk 4: State Management Complexity
**Risk**: Complex state might be hard to manage
**Mitigation**:
- Use React Query for server state
- Keep client state minimal
- Clear separation of concerns
- Good documentation

---

## 📝 Next Steps

1. **User Approval**: Get approval on this plan
2. **Team Assignment**: Assign backend and frontend developers
3. **Environment Setup**: Setup development environments
4. **Kickoff**: Start Phase 1 (Backend API)

---

## 📚 Resources

### Documentation
- [Expo Documentation](https://docs.expo.dev/)
- [React Native Documentation](https://reactnative.dev/)
- [React Navigation](https://reactnavigation.org/)
- [Victory Charts](https://formidable.com/open-source/victory/)

### Tutorials
- [Expo Router Tutorial](https://docs.expo.dev/router/introduction/)
- [React Query Tutorial](https://tanstack.com/query/latest/docs/framework/react/overview)
- [Flask JWT Tutorial](https://flask-jwt-extended.readthedocs.io/)

### Design Inspiration
- [Dribbble - Financial Apps](https://dribbble.com/tags/financial-app)
- [Mobbin - Finance Category](https://mobbin.com/browse/ios/apps)

---

**Total Estimated Timeline**: 9-10 weeks (2.5 months)
**Team Size**: 2-3 developers (1 backend, 1-2 frontend)
**Effort**: ~400-500 hours total

---

## 🎉 Expected Benefits

1. **Cross-Platform**: Single codebase for iOS, Android, Web
2. **Modern UX**: Beautiful, intuitive interface
3. **Better Performance**: Faster, more responsive
4. **Offline Support**: Possible with React Query caching
5. **Push Notifications**: Native mobile notifications
6. **App Store Presence**: iOS and Android app stores
7. **Easier Maintenance**: Modern, well-structured codebase
8. **Future-Proof**: Easy to extend with new features

---

**Status**: 📋 Ready for approval and implementation
