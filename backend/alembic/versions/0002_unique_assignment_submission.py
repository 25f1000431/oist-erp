"""Ensure a student has one replaceable submission per assignment.

Revision ID: 0002_assignment_submission_unique
Revises: 0001_initial
Create Date: 2026-11-28
"""

from sqlalchemy import inspect

from alembic import op

revision = "0002_assignment_submission_unique"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    unique_pairs = {
        tuple(item["column_names"])
        for item in inspector.get_unique_constraints("assignment_submission")
    }
    unique_pairs.update(
        tuple(item["column_names"])
        for item in inspector.get_indexes("assignment_submission")
        if item["unique"]
    )
    if ("assignment_id", "student_id") not in unique_pairs:
        op.create_index(
            "uq_assignment_submission_assignment_student",
            "assignment_submission",
            ["assignment_id", "student_id"],
            unique=True,
        )


def downgrade() -> None:
    if any(
        item["name"] == "uq_assignment_submission_assignment_student"
        for item in inspect(op.get_bind()).get_indexes("assignment_submission")
    ):
        op.drop_index(
            "uq_assignment_submission_assignment_student",
            table_name="assignment_submission",
        )
