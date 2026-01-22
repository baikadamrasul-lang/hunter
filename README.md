# Hunter - PC Club Admin Web App

A Flask-based web application for managing PC club bookings, zones, and waitlists.

## Features

- **Admin Authentication**: Secure login with password protection
- **Pending Bookings Management**: View, confirm, cancel, or delete pending booking groups
- **Bookings List**: Filter and manage all bookings with delete functionality
- **PC Management**: View all PCs and toggle their active status
- **Zones**: View all zones with pricing information
- **Waitlist**: Track customer waitlist entries
- **Smart Create**: Intelligent booking creation flow that shows available PCs for selected time slots

## Setup

### Prerequisites

- Python 3.7 or higher
- pip (Python package manager)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/baikadamrasul-lang/hunter.git
cd hunter
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set the admin password environment variable:
```bash
export ADMIN_WEB_PASS=your_secure_password  # On Windows: set ADMIN_WEB_PASS=your_secure_password
```

5. (Optional) Enable debug mode for development:
```bash
export FLASK_DEBUG=true  # On Windows: set FLASK_DEBUG=true
```

### Running the Application

Start the Flask development server:
```bash
python admin_app.py
```

The application will be available at `http://localhost:5000`

### First Run

On first run, the application will:
- Initialize the SQLite database (`club.db`)
- Create all necessary tables
- Seed the database with zones and PCs from `settings.json`

## Configuration

### settings.json

The `settings.json` file contains:

- **CLUB_TZ**: Timezone for the club (e.g., "Asia/Almaty")
- **SEED**: Initial data for zones and PCs
  - **zones**: List of zones with names and hourly rates
    - STANDART (500 ₸/hour)
    - COMFORT (700 ₸/hour)
    - VIP (1000 ₸/hour)
    - BOOT CAMP (600 ₸/hour)
    - PREMIUM ZONE (1200 ₸/hour)
  - **pcs**: List of PCs with their zone assignments
    - STANDART: PCs 1-25
    - COMFORT: PCs 26-43
    - BOOT CAMP: PCs 44-53
    - VIP: PCs 101-105
    - PREMIUM ZONE: PCs 106-115

## Usage

1. **Login**: Navigate to the application URL and log in with the password set in `ADMIN_WEB_PASS`

2. **View Pending Bookings**: Click "Pending" to see all pending booking groups
   - Confirm a group to mark bookings as confirmed
   - Cancel a group to mark bookings as cancelled
   - Delete a group to permanently remove pending bookings

3. **Manage Bookings**: Click "Bookings" to view all bookings
   - Filter by zone or status
   - Delete individual bookings

4. **Manage PCs**: Click "PCs" to view all PCs
   - Toggle PC active/inactive status

5. **View Zones**: Click "Zones" to see all zones and their pricing

6. **View Waitlist**: Click "Waitlist" to see customer waitlist entries

7. **Smart Create**: Click "Smart Create" to create new bookings
   - Select zone, start time, duration, and number of PCs
   - View available PCs for the selected time slot
   - Choose specific PCs and create bookings

## Database Schema

- **zones**: PC zones with pricing
- **pcs**: Individual PCs assigned to zones
- **bookings**: Booking records with time slots and status
- **waitlist**: Customer waitlist entries

## Security

- Admin access is protected by password authentication via `ADMIN_WEB_PASS` environment variable
- Session-based authentication with Flask sessions
- Database stored in SQLite file (`club.db`)

## License

MIT