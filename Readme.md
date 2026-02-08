# Anti-Bullying Reporting System

A web-based platform that allows students to anonymously report bullying incidents and receive support from trained psychologists. The system incorporates machine learning to automatically categorize reports and prioritize urgent cases.

## Features

- **Anonymous Reporting**: Students can submit reports without revealing their identity
- **ML-Powered Classification**: Automatic categorization of reports using LightGBM model
- **Priority Assessment**: Reports are prioritized based on severity (suicide, threats, weapons, offline crime)
- **Secure Token-Based Chat**: Anonymous ongoing communication between students and psychologists
- **Admin Dashboard**: Psychologists can manage and respond to reports
- **Audit Logging**: Comprehensive logging of administrative actions

## Technologies Used

- **Backend**: Flask (Python 3.11+)
- **Database**: SQLite with SQLAlchemy ORM
- **Machine Learning**: LightGBM, scikit-learn, TF-IDF vectorizer
- **Frontend**: HTML templates with JavaScript
- **Dependencies**: See [requirements.txt](requirements.txt)

## Architecture

The system consists of:
- Flask web application serving the API and frontend
- SQLite database storing reports, messages, and user data
- Pre-trained LightGBM model for text classification
- TF-IDF vectorizer for text preprocessing
- Secure token-based authentication system

## Models

The system uses two pre-trained machine learning models:
- `lgbm_model_toxic_.pkl`: LightGBM model for classifying text into categories
- `tfidf_vectorizer.pkl`: TF-IDF vectorizer for converting text to numerical features

Categories include: suicide, offline_crime, weapons, threat, toxic, neutral, spam

## Database Schema

The application uses the following main tables:

- **Tickets**: Stores individual reports with category, priority, and status
- **Tokens**: Secure tokens linking students to their reports
- **Messages**: Chat history between students and psychologists
- **Tags**: ML-generated tags with probability scores
- **AuditLog**: Logs of administrative actions
- **UserAdmin**: Psychologist accounts with role-based access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/your-repo/anti-bullying-system.git
cd anti-bullying-system
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure you have the required ML model files:
- `lgbm_model_toxic_.pkl`
- `tfidf_vectorizer.pkl`

4. Run the application:
```bash
python flask_app.py
```

The application will be accessible at `http://localhost:8080`

## Default Admin Credentials

For initial access, the system creates a default admin account:
- **Username**: psychologist
- **Password**: psychologist123

## API Endpoints

### Public Endpoints
- `POST /api/report` - Submit a new report
- `POST /api/chat` - Send a message using a token
- `POST /api/chat/token` - Get chat history using a token

### Admin Endpoints
- `POST /api/admin/login` - Authenticate admin user
- `GET /api/admin/tickets` - Get filtered/paginated tickets
- `PUT /api/admin/tickets/{id}/status` - Update ticket status
- `PUT /api/admin/tickets/{id}/priority` - Update ticket priority
- `GET/POST /api/admin/tickets/{id}/chat` - Get/send messages for a ticket
- `POST /api/admin/logout` - Logout admin user
- `GET /api/admin/messages` - Get all messages with filters

## Frontend Pages

- `/` - Home page
- `/login` - Login page for psychologists
- `/admin` - Admin dashboard
- `/chat/{token}` - Anonymous chat interface
- `/about`, `/how-it-works`, `/contact`, `/faq`, `/privacy-policy` - Information pages

## Security Features

- Secure token generation using `secrets.token_urlsafe()`
- Password hashing using SHA-256
- Session-based authentication for admin panel
- Input validation and sanitization
- Audit logging of administrative actions

## Machine Learning Pipeline

The system preprocesses text by:
1. Converting to lowercase
2. Removing URLs, mentions, hashtags
3. Removing punctuation and digits
4. Normalizing whitespace
5. Vectorizing with TF-IDF
6. Classifying with LightGBM model

High-priority categories trigger immediate attention from psychologists.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support, contact the development team or create an issue in the GitHub repository.