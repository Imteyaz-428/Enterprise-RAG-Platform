"""ingestion and database hardening

Revision ID: 002_ingestion_hardening
Revises: 001_baseline
Create Date: 2026-11-21

"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_ingestion_hardening'
down_revision: Union[str, None] = '001_baseline'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. documents.file_hash (String(64), nullable)
    op.add_column('documents', sa.Column('file_hash', sa.String(length=64), nullable=True))

    # 2. documents.error_message (Text, nullable)
    op.add_column('documents', sa.Column('error_message', sa.Text(), nullable=True))

    # 3. unique index on (organization_id, file_hash) where file_hash IS NOT NULL
    op.create_index(
        'uq_documents_org_file_hash',
        'documents',
        ['organization_id', 'file_hash'],
        unique=True,
        postgresql_where=sa.text('file_hash IS NOT NULL'),
    )

    # 4. document_chunks.organization_id (FK organizations.id ON DELETE CASCADE),
    #    backfilled from documents then NOT NULL
    op.add_column('document_chunks', sa.Column('organization_id', sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE document_chunks
        SET organization_id = documents.organization_id
        FROM documents
        WHERE document_chunks.document_id = documents.id
        """
    )
    op.alter_column('document_chunks', 'organization_id', nullable=False)
    op.create_foreign_key(
        'fk_document_chunks_organization_id_organizations',
        'document_chunks',
        'organizations',
        ['organization_id'],
        ['id'],
        ondelete='CASCADE',
    )

    # 5. indexes:
    # document_chunks(organization_id)
    op.create_index(
        'ix_document_chunks_organization_id',
        'document_chunks',
        ['organization_id'],
        unique=False,
    )

    # GIN index on to_tsvector('english', chunk_text)
    op.execute(
        "CREATE INDEX ix_document_chunks_chunk_text_tsv ON document_chunks USING gin (to_tsvector('english', chunk_text))"
    )

    # HNSW index on the embedding column with vector_cosine_ops (ivfflat if HNSW is unavailable)
    if context.is_offline_mode():
        op.execute(
            "CREATE INDEX ix_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops)"
        )
    else:
        conn = op.get_bind()
        has_hnsw = False
        try:
            res = conn.execute(sa.text("SELECT 1 FROM pg_am WHERE amname = 'hnsw'")).scalar()
            has_hnsw = bool(res)
        except Exception:
            has_hnsw = False

        if has_hnsw:
            op.execute(
                "CREATE INDEX ix_document_chunks_embedding ON document_chunks USING hnsw (embedding vector_cosine_ops)"
            )
        else:
            op.execute(
                "CREATE INDEX ix_document_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops)"
            )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_embedding")
    op.execute("DROP INDEX IF EXISTS ix_document_chunks_chunk_text_tsv")
    op.drop_index('ix_document_chunks_organization_id', table_name='document_chunks')
    op.drop_constraint('fk_document_chunks_organization_id_organizations', 'document_chunks', type_='foreignkey')
    op.drop_column('document_chunks', 'organization_id')
    op.drop_index('uq_documents_org_file_hash', table_name='documents', postgresql_where=sa.text('file_hash IS NOT NULL'))
    op.drop_column('documents', 'error_message')
    op.drop_column('documents', 'file_hash')
