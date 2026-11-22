"""database integrity and foreign key on-delete rules

Revision ID: 003_db_integrity
Revises: 002_ingestion_hardening
Create Date: 2026-11-21

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_db_integrity'
down_revision: Union[str, None] = '002_ingestion_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("documents") as batch_op:
            batch_op.alter_column("uploaded_by", existing_type=sa.Integer(), nullable=True)
            batch_op.drop_constraint("documents_uploaded_by_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "documents_uploaded_by_fkey",
                "users",
                ["uploaded_by"],
                ["id"],
                ondelete="SET NULL",
            )
            batch_op.drop_constraint("documents_organization_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "documents_organization_id_fkey",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )

        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_constraint("users_organization_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "users_organization_id_fkey",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )

        with op.batch_alter_table("chat_sessions") as batch_op:
            batch_op.drop_constraint("chat_sessions_organization_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "chat_sessions_organization_id_fkey",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.drop_constraint("chat_sessions_user_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "chat_sessions_user_id_fkey",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )

        with op.batch_alter_table("chat_messages") as batch_op:
            batch_op.drop_constraint("chat_messages_session_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "chat_messages_session_id_fkey",
                "chat_sessions",
                ["session_id"],
                ["id"],
                ondelete="CASCADE",
            )
    else:
        # PostgreSQL dialect
        # 1. users.organization_id -> CASCADE
        op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey")
        op.create_foreign_key(
            "users_organization_id_fkey",
            "users",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 2. documents.organization_id -> CASCADE
        op.drop_constraint("documents_organization_id_fkey", "documents", type_="foreignkey")
        op.create_foreign_key(
            "documents_organization_id_fkey",
            "documents",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 3. documents.uploaded_by -> SET NULL (make it nullable)
        op.alter_column("documents", "uploaded_by", existing_type=sa.Integer(), nullable=True)
        op.drop_constraint("documents_uploaded_by_fkey", "documents", type_="foreignkey")
        op.create_foreign_key(
            "documents_uploaded_by_fkey",
            "documents",
            "users",
            ["uploaded_by"],
            ["id"],
            ondelete="SET NULL",
        )

        # 4. chat_sessions.organization_id -> CASCADE
        op.drop_constraint("chat_sessions_organization_id_fkey", "chat_sessions", type_="foreignkey")
        op.create_foreign_key(
            "chat_sessions_organization_id_fkey",
            "chat_sessions",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 5. chat_sessions.user_id -> CASCADE
        op.drop_constraint("chat_sessions_user_id_fkey", "chat_sessions", type_="foreignkey")
        op.create_foreign_key(
            "chat_sessions_user_id_fkey",
            "chat_sessions",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 6. chat_messages.session_id -> CASCADE
        op.drop_constraint("chat_messages_session_id_fkey", "chat_messages", type_="foreignkey")
        op.create_foreign_key(
            "chat_messages_session_id_fkey",
            "chat_messages",
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "sqlite":
        with op.batch_alter_table("chat_messages") as batch_op:
            batch_op.drop_constraint("chat_messages_session_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "chat_messages_session_id_fkey",
                "chat_sessions",
                ["session_id"],
                ["id"],
                ondelete="CASCADE",
            )

        with op.batch_alter_table("chat_sessions") as batch_op:
            batch_op.drop_constraint("chat_sessions_user_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "chat_sessions_user_id_fkey",
                "users",
                ["user_id"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.drop_constraint("chat_sessions_organization_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "chat_sessions_organization_id_fkey",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )

        with op.batch_alter_table("documents") as batch_op:
            batch_op.drop_constraint("documents_uploaded_by_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "documents_uploaded_by_fkey",
                "users",
                ["uploaded_by"],
                ["id"],
                ondelete="CASCADE",
            )
            batch_op.alter_column("uploaded_by", existing_type=sa.Integer(), nullable=False)
            batch_op.drop_constraint("documents_organization_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "documents_organization_id_fkey",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )

        with op.batch_alter_table("users") as batch_op:
            batch_op.drop_constraint("users_organization_id_fkey", type_="foreignkey")
            batch_op.create_foreign_key(
                "users_organization_id_fkey",
                "organizations",
                ["organization_id"],
                ["id"],
                ondelete="CASCADE",
            )
    else:
        # PostgreSQL
        # 6. chat_messages.session_id
        op.drop_constraint("chat_messages_session_id_fkey", "chat_messages", type_="foreignkey")
        op.create_foreign_key(
            "chat_messages_session_id_fkey",
            "chat_messages",
            "chat_sessions",
            ["session_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 5. chat_sessions.user_id
        op.drop_constraint("chat_sessions_user_id_fkey", "chat_sessions", type_="foreignkey")
        op.create_foreign_key(
            "chat_sessions_user_id_fkey",
            "chat_sessions",
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 4. chat_sessions.organization_id
        op.drop_constraint("chat_sessions_organization_id_fkey", "chat_sessions", type_="foreignkey")
        op.create_foreign_key(
            "chat_sessions_organization_id_fkey",
            "chat_sessions",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 3. documents.uploaded_by -> restore nullable=False, CASCADE
        op.drop_constraint("documents_uploaded_by_fkey", "documents", type_="foreignkey")
        op.create_foreign_key(
            "documents_uploaded_by_fkey",
            "documents",
            "users",
            ["uploaded_by"],
            ["id"],
            ondelete="CASCADE",
        )
        op.alter_column("documents", "uploaded_by", existing_type=sa.Integer(), nullable=False)

        # 2. documents.organization_id
        op.drop_constraint("documents_organization_id_fkey", "documents", type_="foreignkey")
        op.create_foreign_key(
            "documents_organization_id_fkey",
            "documents",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )

        # 1. users.organization_id
        op.drop_constraint("users_organization_id_fkey", "users", type_="foreignkey")
        op.create_foreign_key(
            "users_organization_id_fkey",
            "users",
            "organizations",
            ["organization_id"],
            ["id"],
            ondelete="CASCADE",
        )
