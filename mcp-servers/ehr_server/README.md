# EHR MCP Server

A comprehensive Model Context Protocol (MCP) server for Electronic Health Records (EHR) integration in healthcare care gap automation systems.

## Features

- **HIPAA-compliant** data handling with encryption and audit logging
- **PostgreSQL integration** using shared SQLAlchemy models
- **Comprehensive EHR tools** for patient management and care gap tracking
- **Robust error handling** and logging
- **Test suite** for reliability assurance

## Tools Available

### 1. get_overdue_patients
Retrieve patients with overdue care gap screenings with optional filters.

**Parameters:**
- `min_age` (optional): Minimum patient age (0-150)
- `max_age` (optional): Maximum patient age (0-150)
- `screening_type` (optional): Type of screening (e.g., 'mammogram', 'colonoscopy')
- `min_overdue_days` (optional): Minimum days overdue
- `max_overdue_days` (optional): Maximum days overdue
- `priority_level` (optional): Priority level ('low', 'medium', 'high', 'urgent')
- `limit` (optional): Maximum results to return (1-100, default: 50)

### 2. get_patient_details
Get comprehensive information for a specific patient including care gaps and appointments.

**Parameters:**
- `patient_id` (required): Patient ID (integer)

### 3. update_patient_record
Update patient record information with validation and audit logging.

**Parameters:**
- `patient_id` (required): Patient ID (integer)
- `updates` (required): Object containing fields to update:
  - `name` (string)
  - `age` (integer, 0-150)
  - `email` (string, email format)
  - `phone` (string)
  - `insurance_info` (object)
  - `risk_factors` (string)
  - `preferred_contact_method` ('email', 'phone', 'sms', 'mail')

### 4. close_care_gap
Mark a care gap as closed/completed with optional completion date.

**Parameters:**
- `care_gap_id` (required): Care gap ID (integer)
- `completion_date` (optional): Date when screening was completed (YYYY-MM-DD)
- `notes` (optional): Notes about the completion

## Setup and Installation

### Prerequisites
- Python 3.11+
- PostgreSQL database
- MCP Python SDK

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables in `.env`:
```bash
# Database Configuration
DATABASE_URL=postgresql://postgres:user@localhost:5433/healthcare_care_gap
DATABASE_ECHO=false

# Security Configuration
ENCRYPTION_KEY=your-encryption-key-here
AUDIT_LOG_ENABLED=true

# Logging Configuration
LOG_LEVEL=INFO
```

### Database Setup

The server uses shared SQLAlchemy models from the main backend application. Ensure your database is set up with the required tables:

```bash
# From the backend directory
cd ../../backend
alembic upgrade head
```

## Usage

### Running the Server

```bash
python server.py
```

### Testing the Server

1. Generate sample data:
```bash
python generate_sample_data.py --patients 30
```

2. Run the test suite:
```bash
python test_server.py
```

3. Interactive client testing:
```bash
python client.py
```

### MCP Integration

To integrate with MCP clients, use the server as a stdio MCP server:

```json
{
  "mcpServers": {
    "healthcare-ehr": {
      "command": "python",
      "args": ["/path/to/ehr_server/server.py"],
      "env": {
        "DATABASE_URL": "postgresql://user:pass@host:port/db"
      }
    }
  }
}
```

## Security Features

### HIPAA Compliance
- **Data Encryption**: Sensitive patient data is encrypted at rest
- **Audit Logging**: All data access and modifications are logged
- **Access Controls**: Input validation and sanitization
- **Data Anonymization**: Patient IDs are hashed in audit logs

### Audit Logging
All operations generate audit events including:
- Patient data access
- Record modifications
- Care gap closures
- System errors

Audit logs are structured JSON entries with:
- Timestamp
- Event type
- Anonymized patient identifier
- User/system identifier
- Operation details

## File Structure

```
ehr_server/
├── __init__.py                 # Package initialization
├── server.py                   # Main MCP server implementation
├── client.py                   # Test client for server interaction
├── database.py                 # Database configuration and models
├── config.py                   # Server configuration
├── security.py                 # HIPAA security and encryption
├── generate_sample_data.py     # Sample data generation
├── test_server.py              # Comprehensive test suite
├── requirements.txt            # Python dependencies
├── audit_logging.conf          # Logging configuration
└── README.md                   # This file
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:user@localhost:5433/healthcare_care_gap` |
| `DATABASE_ECHO` | Enable SQLAlchemy query logging | `false` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `ENCRYPTION_KEY` | Key for data encryption | None |
| `AUDIT_LOG_ENABLED` | Enable audit logging | `true` |

### Database Models

The server uses shared models from the main application:
- **Patient**: Core patient information
- **CareGap**: Care gap tracking with status and priorities
- **Appointment**: Scheduled appointments linked to care gaps

## Error Handling

The server includes comprehensive error handling:
- Input validation with descriptive error messages
- Database connection error recovery
- Graceful handling of missing records
- Structured error responses in JSON format

## Testing

The test suite includes:
- Server connectivity tests
- Tool functionality validation
- Filter parameter testing
- Error condition handling
- CRUD operation verification

Run tests with:
```bash
python test_server.py
```

## Contributing

1. Follow the existing code style and patterns
2. Add tests for new functionality
3. Update documentation for API changes
4. Ensure HIPAA compliance for any patient data handling
5. Add appropriate audit logging for new operations

## License

This project is part of the Healthcare Care Gap Automation system and follows the same licensing terms.