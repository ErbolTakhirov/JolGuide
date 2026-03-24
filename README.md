# JolGit - Platform for Local Guides

JolGit is a web application designed to connect tourists with professional local guides. It facilitates booking, chatting, and reviewing experiences.

## Features
- User registration and profiles (Tourists and Guides)
- Guide search and matching
- Booking system
- Real-time chat (planned/integrated)
- Reviews and ratings

## Tech Stack
- **Backend:** Django 4.2
- **Database:** SQLite (default)
- **Styling:** CSS
- **AI Integration:** Google Generative AI (Wayfinder)

## Getting Started

### Prerequisites
- Python 3.10+
- `pip`

### Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/JolGit.git
   cd JolGit
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run migrations:
   ```bash
   python manage.py migrate
   ```
5. Start the development server:
   ```bash
   python manage.py run_server
   ```

## License
MIT
