import os
from typing import Any, Dict, Optional

import pymysql
from dotenv import load_dotenv


load_dotenv()


def get_connection() -> pymysql.connections.Connection:
	"""Create a new DB connection using env vars.

	Returns a fresh connection. FastAPI dependencies will open/close per-request.
	"""
	host = os.getenv("HOST")
	port = int(os.getenv("PORT_NUMBER", "3306"))
	database = os.getenv("DATABASE_NAME")
	user = os.getenv("DATABASE_USER")
	password = os.getenv("DATABASE_PASSWORD")

	return pymysql.connect(
		host=host,
		user=user,
		password=password,
		database=database,
		port=port,
		charset="utf8mb4",
		cursorclass=pymysql.cursors.DictCursor,
		autocommit=True,
	)


def call_sp_insert_patient(
	conn: pymysql.connections.Connection,
	patient: Dict[str, Any],
	changed_by: Optional[str] = None,
) -> Dict[str, Any]:
	"""Invoke sp_insert_patient for validated patient creation."""
	with conn.cursor() as cur:
		cur.callproc(
			"sp_insert_patient",
			[
				patient.get("patient_id"),
				patient.get("name"),
				patient.get("age"),
				patient.get("arrival_date"),
				patient.get("departure_date"),
				patient.get("service"),
				patient.get("satisfaction"),
				changed_by or "api_user",
			],
		)
		rows = cur.fetchall()
		# stored proc SELECT returns status info
		return rows[0] if rows else {"status": "unknown"}


def query_one(conn: pymysql.connections.Connection, sql: str, params: tuple) -> Optional[Dict[str, Any]]:
	with conn.cursor() as cur:
		cur.execute(sql, params)
		row = cur.fetchone()
		return row


def query_all(conn: pymysql.connections.Connection, sql: str, params: tuple = ()) -> list[Dict[str, Any]]:
	with conn.cursor() as cur:
		cur.execute(sql, params)
		rows = cur.fetchall()
		return list(rows)


def execute(conn: pymysql.connections.Connection, sql: str, params: tuple) -> int:
	with conn.cursor() as cur:
		cur.execute(sql, params)
		return cur.rowcount

