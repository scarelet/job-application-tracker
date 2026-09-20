# Job Application Tracker

![Job Application Tracker Dashboard](screenshots/dashboard.png)

A web application for tracking job applications, interviews, offers, and rejections in one place.

## Features

* Add job applications
* Edit existing applications
* Delete applications
* Filter applications by status
* Sort applications by date
* Track application statistics
* REST API for creating, viewing, updating, and deleting applications

## Technologies

* Python
* Flask
* SQLite
* HTML
* CSS
* REST API
* Git/GitHub

## API Endpoints

| Method | Endpoint                 | Description              |
| ------ | ------------------------ | ------------------------ |
| GET    | `/api/applications`      | Get all applications     |
| POST   | `/api/applications`      | Create a new application |
| PUT    | `/api/applications/<id>` | Update an application    |
| DELETE | `/api/applications/<id>` | Delete an application    |

## How to Run

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd jobtracker
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
```

### 3. Activate the virtual environment

```bash
source venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the application

```bash
venv/bin/python -m flask --app app run --port 5001
```

Open your browser and go to:

`http://127.0.0.1:5001`
