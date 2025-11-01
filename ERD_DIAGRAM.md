# Entity Relationship Diagram (ERD)

## Database Schema: Prediction Pipeline

### Overview
This document describes the database schema for the Prediction Pipeline system, including both MySQL (relational) and MongoDB (NoSQL) implementations.

---

## Entity Relationships

```
┌─────────────────┐
│    patients     │
├─────────────────┤
│ patient_id (PK) │
│ name            │
│ age             │
│ arrival_date    │
│ departure_date  │
│ service         │
│ satisfaction    │
└─────────────────┘
       │
       │ (service reference)
       │
       ▼
┌─────────────────┐         ┌──────────────────────┐
│ services_weekly │         │   staff_schedule     │
├─────────────────┤         ├──────────────────────┤
│ id (PK)         │         │ id (PK)              │
│ week            │         │ day_or_shift         │
│ month           │◄────────┤ staff_id (FK)        │
│ service         │         │ staff_name           │
│ available_beds  │         │ role                 │
│ patients_request│         │ service              │
│ patients_admitted│        │ on_shift            │
│ patients_refused│         └──────────────────────┘
│ patient_satisfaction│                │
│ staff_morale    │                   │
│ event           │                   │ (staff_id FK)
└─────────────────┘                   ▼
                              ┌─────────────────┐
                              │     staff       │
                              ├─────────────────┤
                              │ staff_id (PK)   │
                              │ staff_name      │
                              │ role            │
                              │ service         │
                              └─────────────────┘

┌─────────────────┐         ┌──────────────────────┐
│   audit_log    │         │ validation_errors    │
├─────────────────┤         ├──────────────────────┤
│ id (PK)         │         │ id (PK)              │
│ table_name      │         │ table_name           │
│ row_pk          │         │ row_pk               │
│ operation       │         │ error_message        │
│ old_values      │         │ payload              │
│ new_values      │         │ created_at           │
│ changed_at      │         └──────────────────────┘
│ changed_by      │
└─────────────────┘
```

---

## Detailed Entity Descriptions

### 1. patients
**Description**: Stores patient information and visit details

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| patient_id | VARCHAR(64) | PRIMARY KEY | Unique patient identifier |
| name | VARCHAR(255) | NOT NULL | Patient full name |
| age | INT | NULL | Patient age |
| arrival_date | DATE | NULL | Date of arrival |
| departure_date | DATE | NULL | Date of departure |
| service | VARCHAR(64) | NULL | Medical service department |
| satisfaction | INT | NULL, 0-100 | Patient satisfaction score |

**Relationships**:
- `service` references service types used in `services_weekly`

---

### 2. staff
**Description**: Stores healthcare staff information

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| staff_id | VARCHAR(64) | PRIMARY KEY | Unique staff identifier |
| staff_name | VARCHAR(255) | NOT NULL | Staff member full name |
| role | VARCHAR(64) | NULL | Staff role (doctor, nurse, etc.) |
| service | VARCHAR(64) | NULL | Department/service assignment |

**Relationships**:
- Referenced by `staff_schedule.staff_id` (Foreign Key with CASCADE)

**Triggers**:
- `trg_staff_update_log`: Automatically logs all updates to `audit_log`

---

### 3. staff_schedule
**Description**: Tracks staff scheduling and shift assignments

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique schedule entry ID |
| day_or_shift | VARCHAR(64) | NOT NULL | Day of week or shift identifier |
| staff_id | VARCHAR(64) | FOREIGN KEY | Reference to staff.staff_id |
| staff_name | VARCHAR(255) | NULL | Staff name (denormalized) |
| role | VARCHAR(64) | NULL | Staff role (denormalized) |
| service | VARCHAR(64) | NULL | Service department |
| on_shift | TINYINT(1) | DEFAULT 0 | Whether staff is currently on shift |

**Relationships**:
- `staff_id` → `staff.staff_id` (Foreign Key)
  - ON DELETE SET NULL
  - ON UPDATE CASCADE

**Indexes**:
- Index on `staff_id` for foreign key lookups
- Composite index on `(day_or_shift, service)` for availability queries

---

### 4. services_weekly
**Description**: Weekly aggregated metrics for each service department

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique record ID |
| week | INT | NOT NULL | Week number (1-53) |
| month | INT | NOT NULL | Month number (1-12) |
| service | VARCHAR(64) | NOT NULL | Service department name |
| available_beds | INT | NULL | Number of available beds |
| patients_request | INT | NULL | Number of patient requests |
| patients_admitted | INT | NULL | Number of patients admitted |
| patients_refused | INT | NULL | Number of patients refused |
| patient_satisfaction | INT | NULL, 0-100 | Average patient satisfaction |
| staff_morale | INT | NULL, 0-100 | Staff morale score |
| event | VARCHAR(255) | NULL | Special events (flu, donation, etc.) |

**Constraints**:
- UNIQUE KEY on `(week, month, service)` - ensures one record per service per week/month

**Relationships**:
- `service` column references service types used across the system

---

### 5. audit_log
**Description**: System-wide audit trail for tracking data changes

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique log entry ID |
| table_name | VARCHAR(128) | NOT NULL | Name of table that was changed |
| row_pk | VARCHAR(255) | NULL | Primary key value of changed row |
| operation | VARCHAR(16) | NOT NULL | Type of operation (INSERT, UPDATE, DELETE) |
| old_values | LONGTEXT | NULL | JSON-like string of old values |
| new_values | LONGTEXT | NULL | JSON-like string of new values |
| changed_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Timestamp of change |
| changed_by | VARCHAR(128) | NULL | User or system that made the change |

**Usage**:
- Populated by stored procedures and triggers
- Used for compliance and debugging

---

### 6. validation_errors
**Description**: Logs validation errors during data insertion

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INT | PRIMARY KEY, AUTO_INCREMENT | Unique error entry ID |
| table_name | VARCHAR(128) | NOT NULL | Table where error occurred |
| row_pk | VARCHAR(255) | NULL | Primary key of failed record |
| error_message | TEXT | NULL | Description of validation error |
| payload | LONGTEXT | NULL | JSON-like string of attempted data |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | When error occurred |

**Usage**:
- Populated by stored procedures during validation failures
- Helps identify data quality issues

---

## Stored Procedures

### 1. sp_log_change
**Purpose**: Logs changes to audit_log table

**Parameters**:
- `p_table_name`: Table name
- `p_row_pk`: Primary key value
- `p_operation`: Operation type (INSERT/UPDATE/DELETE)
- `p_old`: Old values (JSON-like string)
- `p_new`: New values (JSON-like string)
- `p_user`: User identifier

---

### 2. sp_insert_patient
**Purpose**: Validates and inserts patient records with automatic audit logging

**Features**:
- Validates age >= 0
- Validates satisfaction between 0-100
- Logs validation errors to `validation_errors` table
- Automatically calls `sp_log_change` on successful insert

---

### 3. sp_check_staff_availability
**Purpose**: Counts available staff for a given service and shift

**Parameters**:
- `p_service`: Service department
- `p_shift`: Shift/day identifier

**Returns**: Count of staff on shift

---

### 4. sp_calculate_service_metrics
**Purpose**: Retrieves weekly metrics for a specific service

**Parameters**:
- `p_service`: Service department
- `p_week`: Week number
- `p_month`: Month number

**Returns**: Service metrics for the specified period

---

## Triggers

### trg_staff_update_log
**Event**: AFTER UPDATE on `staff` table

**Purpose**: Automatically logs all staff table updates to audit_log

**Actions**:
1. Captures OLD and NEW values
2. Converts to JSON-like format
3. Calls `sp_log_change` to log the update

---

## MongoDB Schema (NoSQL)

MongoDB collections mirror the MySQL tables with the same structure:

### Collections:
1. **patients** - Patient documents
2. **staff** - Staff documents
3. **staff_schedule** - Schedule documents
4. **services_weekly** - Weekly metrics documents
5. **audit_log** - Audit trail documents
6. **validation_errors** - Validation error documents

### Indexes (MongoDB):
- Unique indexes on primary key fields (`patient_id`, `staff_id`)
- Indexes on foreign key fields (`staff_id` in staff_schedule)
- Composite indexes for common queries
- Indexes on date/timestamp fields for sorting

### Relationships in MongoDB:
- **Embedded References**: Relationships are maintained through field references (e.g., `staff_id` in `staff_schedule`)
- **Application-level Joins**: Relationships are handled at the application level rather than database-level joins
- **Denormalization**: Some fields like `staff_name` are stored redundantly for performance

---

## Normalization Level

The schema follows **Third Normal Form (3NF)**:
- ✅ **1NF**: All columns contain atomic values
- ✅ **2NF**: All non-key attributes fully dependent on primary key
- ✅ **3NF**: No transitive dependencies (non-key attributes depend only on the primary key)

**Denormalization Examples** (intentional for performance):
- `staff_schedule` contains `staff_name` and `role` (redundant but improves query performance)
- These are maintained by application logic or could be updated via triggers

---

## ERD Visualization Tools

To generate a visual ERD diagram, you can use:

1. **dbdiagram.io** (Free, online):
   - Go to https://dbdiagram.io
   - Use the syntax below or import this document

2. **Draw.io / Lucidchart**:
   - Manual creation using the entity descriptions above

3. **MySQL Workbench**:
   - Reverse engineer from the database
   - Tools → Database → Reverse Engineer

### dbdiagram.io Syntax:

```sql
Table patients {
  patient_id varchar(64) [pk]
  name varchar(255) [not null]
  age int
  arrival_date date
  departure_date date
  service varchar(64)
  satisfaction int
}

Table staff {
  staff_id varchar(64) [pk]
  staff_name varchar(255) [not null]
  role varchar(64)
  service varchar(64)
}

Table staff_schedule {
  id int [pk, increment]
  day_or_shift varchar(64) [not null]
  staff_id varchar(64) [ref: > staff.staff_id]
  staff_name varchar(255)
  role varchar(64)
  service varchar(64)
  on_shift tinyint(1) [default: 0]
}

Table services_weekly {
  id int [pk, increment]
  week int [not null]
  month int [not null]
  service varchar(64) [not null]
  available_beds int
  patients_request int
  patients_admitted int
  patients_refused int
  patient_satisfaction int
  staff_morale int
  event varchar(255)
  indexes {
    (week, month, service) [unique]
  }
}

Table audit_log {
  id int [pk, increment]
  table_name varchar(128) [not null]
  row_pk varchar(255)
  operation varchar(16) [not null]
  old_values longtext
  new_values longtext
  changed_at timestamp [default: `CURRENT_TIMESTAMP`]
  changed_by varchar(128)
}

Table validation_errors {
  id int [pk, increment]
  table_name varchar(128) [not null]
  row_pk varchar(255)
  error_message text
  payload longtext
  created_at timestamp [default: `CURRENT_TIMESTAMP`]
}
```

---

## Notes

- All date fields use MySQL DATE type
- Satisfaction and morale scores are integers (0-100)
- LONGTEXT is used for JSON-like strings to ensure compatibility
- Foreign keys use CASCADE for updates to maintain referential integrity
- Auto-increment IDs are used for generated primary keys where appropriate
- VARCHAR lengths are designed to accommodate realistic data sizes

