import os
from dotenv import load_dotenv
import pymysql

load_dotenv()

HOST = os.getenv("HOST")
PORT = int(os.getenv("PORT_NUMBER", 3306))
DB = os.getenv("DATABASE_NAME")
USER = os.getenv("DATABASE_USER")
PASSWORD = os.getenv("DATABASE_PASSWORD")

# Connect with autocommit so CREATE/PROCEDURE statements apply immediately
conn = pymysql.connect(
    host=HOST,
    user=USER,
    password=PASSWORD,
    database=DB,
    port=PORT,
    autocommit=True,
    charset="utf8mb4"
)

create_table_statements = [
    """
    CREATE TABLE IF NOT EXISTS patients (
        patient_id VARCHAR(64) PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        age INT,
        arrival_date DATE,
        departure_date DATE,
        service VARCHAR(64),
        satisfaction INT
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS staff (
        staff_id VARCHAR(64) PRIMARY KEY,
        staff_name VARCHAR(255) NOT NULL,
        role VARCHAR(64),
        service VARCHAR(64)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS staff_schedule (
        id INT AUTO_INCREMENT PRIMARY KEY,
        day_or_shift VARCHAR(64) NOT NULL,
        staff_id VARCHAR(64),
        staff_name VARCHAR(255),
        role VARCHAR(64),
        service VARCHAR(64),
        on_shift TINYINT(1) DEFAULT 0,
        FOREIGN KEY (staff_id) REFERENCES staff(staff_id)
            ON DELETE SET NULL ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS services_weekly (
        id INT AUTO_INCREMENT PRIMARY KEY,
        `week` INT NOT NULL,
        `month` INT NOT NULL,
        service VARCHAR(64) NOT NULL,
        available_beds INT,
        patients_request INT,
        patients_admitted INT,
        patients_refused INT,
        patient_satisfaction INT,
        staff_morale INT,
        event VARCHAR(255),
        UNIQUE KEY uix_week_month_service (`week`,`month`,`service`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        id INT AUTO_INCREMENT PRIMARY KEY,
        table_name VARCHAR(128) NOT NULL,
        row_pk VARCHAR(255),
        operation VARCHAR(16) NOT NULL,
        old_values LONGTEXT,
        new_values LONGTEXT,
        changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        changed_by VARCHAR(128)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """,
    """
    CREATE TABLE IF NOT EXISTS validation_errors (
        id INT AUTO_INCREMENT PRIMARY KEY,
        table_name VARCHAR(128) NOT NULL,
        row_pk VARCHAR(255),
        error_message TEXT,
        payload LONGTEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """
]

# Stored procedures to create (use TEXT / LONGTEXT instead of JSON types)
sp_statements = [
    "DROP PROCEDURE IF EXISTS sp_log_change;",
    "DROP PROCEDURE IF EXISTS sp_insert_patient;",
    """
    CREATE PROCEDURE sp_log_change(
        IN p_table_name VARCHAR(128),
        IN p_row_pk VARCHAR(255),
        IN p_operation VARCHAR(16),
        IN p_old LONGTEXT,
        IN p_new LONGTEXT,
        IN p_user VARCHAR(128)
    )
    BEGIN
        INSERT INTO audit_log (table_name, row_pk, operation, old_values, new_values, changed_by)
        VALUES (p_table_name, p_row_pk, p_operation, p_old, p_new, p_user);
    END;
    """,
    """
    CREATE PROCEDURE sp_insert_patient(
        IN p_patient_id VARCHAR(64),
        IN p_name VARCHAR(255),
        IN p_age INT,
        IN p_arrival_date DATE,
        IN p_departure_date DATE,
        IN p_service VARCHAR(64),
        IN p_satisfaction INT,
        IN p_user VARCHAR(128)
    )
    BEGIN
        DECLARE v_err TEXT DEFAULT NULL;
        DECLARE v_new LONGTEXT DEFAULT NULL;
        DECLARE v_payload LONGTEXT DEFAULT NULL;

        IF p_satisfaction IS NOT NULL AND (p_satisfaction < 0 OR p_satisfaction > 100) THEN
            SET v_err = CONCAT_WS(';', v_err, CONCAT('satisfaction=', p_satisfaction));
        END IF;

        IF p_age IS NOT NULL AND p_age < 0 THEN
            SET v_err = CONCAT_WS(';', v_err, CONCAT('age=', p_age));
        END IF;

        SET v_payload = CONCAT(
            '{',
              '"patient_id":"', IFNULL(p_patient_id,''), '",',
              '"name":"', IFNULL(p_name,''), '",',
              '"age":', IFNULL(CAST(p_age AS CHAR), 'null'), ',',
              '"arrival_date":"', IFNULL(CAST(p_arrival_date AS CHAR), ''), '",',
              '"departure_date":"', IFNULL(CAST(p_departure_date AS CHAR), ''), '",',
              '"service":"', IFNULL(p_service,''), '",',
              '"satisfaction":', IFNULL(CAST(p_satisfaction AS CHAR), 'null'),
            '}'
        );

        IF v_err IS NOT NULL THEN
            INSERT INTO validation_errors (table_name, row_pk, error_message, payload)
            VALUES (
                'patients',
                p_patient_id,
                v_err,
                v_payload
            );
            SELECT 'validation_failed' AS status, v_err AS error_message;
        ELSE
            INSERT INTO patients (patient_id, name, age, arrival_date, departure_date, service, satisfaction)
            VALUES (p_patient_id, p_name, p_age, p_arrival_date, p_departure_date, p_service, p_satisfaction);

            SET v_new = v_payload;

            CALL sp_log_change(
                'patients',
                p_patient_id,
                'INSERT',
                NULL,
                v_new,
                p_user
            );

            SELECT 'inserted' AS status;
        END IF;
    END;
    """
]


def run():
    try:
        with conn.cursor() as cur:
            for stmt in create_table_statements:
                cur.execute(stmt)

            for stmt in sp_statements:
                cur.execute(stmt)

        print("Tables ensured and stored procedures created. (JSON columns replaced with LONGTEXT for compatibility.)")
        print("Use: CALL sp_insert_patient(..., user);")
    finally:
        conn.close()


if __name__ == "__main__":
    run()