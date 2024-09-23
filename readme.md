# FastAPI Real-Time Chat Application

This is a work-in-progress real-time chat application built with FastAPI, WebSockets, and SQLAlchemy. It allows users to create accounts, join chat rooms, and communicate in real-time.

## Features

- User registration and authentication
- Multiple chat rooms
- Real-time messaging using WebSockets
- Message history persistence
- User presence indicators (join/leave notifications)
- Typing indicators

## Tech Stack

- FastAPI: Web framework for building APIs with Python
- WebSockets: For real-time bi-directional communication
- SQLAlchemy: SQL toolkit and ORM
- Jinja2: Template engine for rendering HTML
- SQLite: Database for storing users and messages
- Passlib: Password hashing library

## Setup and Installation

1. Clone the repository (placeholder instructions)
2. Install dependencies:
   ```
   pip install fastapi uvicorn sqlalchemy passlib jinja2
   ```
3. Run the application:
   ```
   python main.py
   ```
4. Access the application at `http://localhost:8000`

## Project Structure

- `main.py`: Main application file containing FastAPI app and WebSocket logic
- `templates/`: Directory containing HTML templates
- `static/`: Directory for static files (CSS, JavaScript)
- `chat.db`: SQLite database file

## TODO

- Implement proper error handling and logging
- Add input validation and sanitization
- Implement user authentication tokens or sessions
- Improve UI/UX design
- Add unit and integration tests
- Implement rate limiting and other security features
- Add support for file sharing and emojis
- Optimize database queries and implement caching
- Create documentation for API endpoints

## Contributing

This project is a work in progress. Contributions, ideas, and feedback are welcome.

## License

[MIT Licence](LICENSE.md) (currently)
